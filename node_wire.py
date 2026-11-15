"""
TD Node Wire - connect and cut operator links by dragging with the right mouse button.

  Alt  + right-drag from one operator to another: connect them
  Ctrl + right-drag away from an operator: cut one of its links, picked by direction
         left = input side, right = output side
         up (or nearly horizontal) = the topmost link, down = the bottommost link

Works in the Network Editor of the main TouchDesigner window. Windows only:
it uses a low-level mouse hook (WH_MOUSE_LL) so the gesture never reaches
TouchDesigner's own right-click handling.

This file is the source of the 'node_wire' Text DAT inside node_wire.tox.
"""
import sys
import ctypes
import types
import traceback
from ctypes import wintypes

LABEL_TITLE = 'NodeWireLabel'   # window title of the cursor label (used to find its handle)
LABEL_OFFSET = 16               # label distance from the cursor (px)
LABEL_H = 22
LABEL_PAD = 16
LABEL_MAXW = 300
REDRAW_MS = 40                  # wait for TouchDesigner to redraw a changed label before showing it
CUT_MIN_DRAG = 20               # cut: shorter drags cancel (px)
CUT_FLAT_DEG = 20               # cut: drags within this angle of horizontal count as "up" (topmost link)

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32
LRESULT = ctypes.c_ssize_t
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
TIMERPROC = ctypes.WINFUNCTYPE(None, wintypes.HWND, ctypes.c_uint, ctypes.c_size_t, wintypes.DWORD)
ENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

u32.SetWindowsHookExW.restype = wintypes.HHOOK
u32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
u32.CallNextHookEx.restype = LRESULT
u32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
u32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
u32.WindowFromPoint.restype = wintypes.HWND
u32.WindowFromPoint.argtypes = [wintypes.POINT]
u32.GetAncestor.restype = wintypes.HWND
u32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
u32.FindWindowW.restype = wintypes.HWND
u32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
u32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
u32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
u32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
u32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
u32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
u32.SetTimer.restype = ctypes.c_size_t
u32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_size_t, ctypes.c_uint, TIMERPROC]
u32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_size_t]
k32.GetModuleHandleW.restype = wintypes.HMODULE


class MSLLHOOKSTRUCT(ctypes.Structure):
	_fields_ = [('pt', wintypes.POINT), ('mouseData', wintypes.DWORD), ('flags', wintypes.DWORD),
				('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]


WM_MOUSEMOVE, WM_RBUTTONDOWN, WM_RBUTTONUP = 0x0200, 0x0204, 0x0205
VK_LBUTTON, VK_CONTROL, VK_MENU = 0x01, 0x11, 0x12
HWND_TOPMOST = wintypes.HWND(-1)
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE, SWP_SHOWWINDOW, SWP_HIDEWINDOW = 0x1, 0x2, 0x10, 0x40, 0x80


# ---------------------------------------------------------------- state

def _comp():
	return me.parent()


def state():
	"""Session-only state, kept on sys so it survives this DAT being recompiled."""
	if not hasattr(sys, '_nodewire'):
		sys._nodewire = types.SimpleNamespace(
			hook=None, proc=None, tdhwnd=0, drag=None, calls=0, last_error=None,
			label_hwnd=0, label_text=None, timer=0, timer_proc=None, pending=None)
	return sys._nodewire


def _down(vk):
	return bool(u32.GetAsyncKeyState(vk) & 0x8000)


# ---------------------------------------------------------------- hook

def install():
	"""Install (or reinstall) the mouse hook. Returns True on success."""
	S = state()
	uninstall()
	S.tdhwnd = _find_td_hwnd()
	S.proc = HOOKPROC(_proc)
	S.hook = u32.SetWindowsHookExW(14, S.proc, k32.GetModuleHandleW(None), 0)   # WH_MOUSE_LL
	return bool(S.hook)


def uninstall():
	S = state()
	if S.hook:
		u32.UnhookWindowsHookEx(S.hook)
	S.hook = None
	S.drag = None
	hide_label()


def _find_td_hwnd():
	"""The main TouchDesigner window of this process."""
	pid = k32.GetCurrentProcessId()
	found = []

	def cb(hwnd, lp):
		p = wintypes.DWORD()
		u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
		if p.value == pid and u32.IsWindowVisible(hwnd):
			buf = ctypes.create_unicode_buffer(256)
			u32.GetWindowTextW(hwnd, buf, 256)
			if buf.value.startswith('TouchDesigner'):
				found.append(hwnd)
		return True
	u32.EnumWindows(ENUMPROC(cb), 0)
	return found[0] if found else 0


def _pt(lParam):
	info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
	return info.pt.x, info.pt.y


def _proc(nCode, wParam, lParam):
	S = sys._nodewire
	S.calls += 1
	try:
		if not me.valid:                    # component deleted: unhook and let everything through
			if S.hook:
				u32.UnhookWindowsHookEx(S.hook)
				S.hook = None
			return u32.CallNextHookEx(None, nCode, wParam, lParam)
	except Exception:
		return u32.CallNextHookEx(None, nCode, wParam, lParam)
	try:
		if nCode == 0:
			if S.drag:
				if wParam == WM_MOUSEMOVE:
					_on_move(*_pt(lParam))
				elif wParam == WM_RBUTTONUP:
					_on_up()
					return 1
				elif wParam == WM_RBUTTONDOWN:
					return 1
			elif wParam == WM_RBUTTONDOWN and not _down(VK_LBUTTON):
				alt, ctrl = _down(VK_MENU), _down(VK_CONTROL)
				if alt or ctrl:
					x, y = _pt(lParam)
					src = _node_at(x, y)
					if src is not None:
						S.drag = {'src': src.path, 'mode': 'connect' if alt else 'cut', 'start': (x, y), 'last': (x, y)}
						if S.tdhwnd and u32.GetForegroundWindow() != S.tdhwnd:
							u32.SetForegroundWindow(S.tdhwnd)
						return 1
	except Exception:
		S.drag = None
		S.last_error = traceback.format_exc()
		try:
			hide_label()
		except Exception:
			pass
	return u32.CallNextHookEx(None, nCode, wParam, lParam)


# ---------------------------------------------------------------- what is under the mouse

def _node_at(sx, sy):
	"""The operator under the screen point (sx, sy) in a Network Editor of the main window, or None."""
	S = state()
	if not S.tdhwnd or u32.GetAncestor(u32.WindowFromPoint(wintypes.POINT(sx, sy)), 2) != S.tdhwnd:
		return None
	if ui.rolloverPar is not None:
		return None
	pt = wintypes.POINT(sx, sy)
	u32.ScreenToClient(S.tdhwnd, ctypes.byref(pt))
	rc = wintypes.RECT()
	u32.GetClientRect(S.tdhwnd, ctypes.byref(rc))
	x, y = pt.x, rc.bottom - pt.y           # TouchDesigner pane coordinates: origin bottom-left
	for p in ui.panes:
		if p.type == PaneType.NETWORKEDITOR and p.bottomLeft.x <= x <= p.topRight.x and p.bottomLeft.y <= y <= p.topRight.y:
			r = ui.rolloverOp
			if r is not None and r.parent() is not None and r.parent() == p.owner:
				return r
	return None


def _target(src_path):
	"""The operator currently under the mouse, if it is a sibling of the drag source."""
	src = op(src_path)
	r = ui.rolloverOp
	if src is None or r is None or r == src or r.parent() != src.parent():
		return None
	return r


# ---------------------------------------------------------------- gesture

def _on_move(x, y):
	S = state()
	S.drag['last'] = (x, y)
	if S.drag['mode'] == 'cut':
		link = _cut_pick(S.drag)
		if link is _TOO_SHORT:
			hide_label()
		elif link is None:
			show_label('✂ (no link)', x, y)
		else:
			show_label('✂ ' + _link_label(op(S.drag['src']), link), x, y)
		return
	tgt = _target(S.drag['src'])
	if tgt is None:
		hide_label()
		return
	show_label('→ ' + tgt.name, x, y)


def _on_up():
	S = state()
	d, S.drag = S.drag, None
	hide_label()
	if d['mode'] == 'cut':
		link = _cut_pick(d)
		if link is _TOO_SHORT or link is None:
			return
		print('[node_wire] ' + cut_link(op(d['src']), link))
		return
	tgt = _target(d['src'])
	if tgt is None:
		return
	print('[node_wire] ' + connect(op(d['src']), tgt)[1])


# ---------------------------------------------------------------- cut by direction

_TOO_SHORT = object()


def _cut_pick(drag):
	"""The link the current drag would cut, None if that side has no link, _TOO_SHORT if the drag is too short.
	Left = input side, right = output side. Up or nearly horizontal = topmost link, down = bottommost."""
	import math
	src = op(drag['src'])
	if src is None:
		return None
	(sx, sy), (x, y) = drag['start'], drag['last']
	dx, dy = x - sx, sy - y                         # dy > 0 = up (screen y grows downward)
	if math.hypot(dx, dy) < CUT_MIN_DRAG:
		return _TOO_SHORT
	flat = abs(dy) <= abs(dx) * math.tan(math.radians(CUT_FLAT_DEG))
	from_top = flat or dy > 0
	links = input_links(src) if dx < 0 else output_links(src)
	if not links:
		return None
	return links[0] if from_top else links[-1]


def input_links(node):
	"""Connected inputs of node, top to bottom (input 0 is the top connector)."""
	return [ic for ic in node.inputConnectors if ic.connections]


def output_links(node):
	"""Every link leaving node, top to bottom by the position of the operator it goes to."""
	links = [ic for oc in node.outputConnectors for ic in oc.connections]
	return sorted(links, key=lambda ic: (-(ic.owner.nodeY + ic.owner.nodeHeight / 2), ic.index))


def _link_label(node, ic):
	if ic.owner == node:                             # an input of node
		src = ic.connections[0].owner.name if ic.connections else '?'
		return 'in {} ← {}'.format(ic.index, src)
	return '→ {} (in {})'.format(ic.owner.name, ic.index)


def cut_link(node, ic):
	"""Cut one link: an input connector of node, or an input connector downstream of node."""
	if ic.owner == node:
		desc = '{} input {} (from {})'.format(node.name, ic.index, ic.connections[0].owner.name if ic.connections else '?')
		ui.undo.startBlock('Node Wire: cut ' + desc)
		try:
			ic.disconnect()
		finally:
			ui.undo.endBlock()
		return 'cut ' + desc
	# output side: remove only the link that comes from node (an input can only hold one link)
	desc = '{} -> {} input {}'.format(node.name, ic.owner.name, ic.index)
	ui.undo.startBlock('Node Wire: cut ' + desc)
	try:
		ic.disconnect()
	finally:
		ui.undo.endBlock()
	return 'cut ' + desc


# ---------------------------------------------------------------- connect / cut

def conn_family(cn):
	"""Family of a connector. A component (e.g. a palette tool) reports the family of
	the in/out operator inside it, so a COMP whose out is a TOP counts as TOP."""
	inner = cn.outOP if cn.isOutput else cn.inOP
	return (inner or cn.owner).family


def connect(src, dst):
	"""Connect src to dst like Blender's Node Wrangler lazy connect: the first output of src
	goes to the first free input of dst with the same family; if all those inputs are taken,
	the first one is replaced. Returns (ok, message)."""
	for oc in src.outputConnectors:
		fam = conn_family(oc)
		same = [ic for ic in dst.inputConnectors if conn_family(ic) == fam]
		if not same:
			continue
		free = next((ic for ic in same if not ic.connections), None)
		ui.undo.startBlock('Node Wire: connect {} -> {}'.format(src.name, dst.name))
		try:
			if free is not None:
				oc.connect(free)
				return True, '{} -> {} (input {})'.format(src.name, dst.name, free.index)
			first = same[0]
			old = first.connections[0].owner.name if first.connections else None
			first.disconnect()
			oc.connect(first)
			return True, '{} -> {} (inputs full, replaced input {}{})'.format(
				src.name, dst.name, first.index, ', was ' + old if old else '')
		finally:
			ui.undo.endBlock()
	return False, 'no matching connectors between {} and {}'.format(src.name, dst.name)


# ---------------------------------------------------------------- cursor label
# A small always-on-top window opened once and kept hidden; moving and showing it with
# the Windows API is instant, and it works while the timeline is paused.

def _own(h):
	if not h or not u32.IsWindow(h):
		return False
	pid = wintypes.DWORD()
	u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
	if pid.value != k32.GetCurrentProcessId():
		return False
	buf = ctypes.create_unicode_buffer(64)
	u32.GetWindowTextW(h, buf, 64)
	return buf.value == LABEL_TITLE


def prepare():
	"""Open the label window once and hide it. Called every frame; cheap once ready."""
	S = state()
	if _own(S.label_hwnd):
		return True
	w = _comp().op('label')
	if not w.isOpen:
		w.par.winoffsetx = -20000
		w.par.winopen.pulse()
		return False                    # the window appears on a later frame
	h = u32.FindWindowW(None, LABEL_TITLE)
	if not h:
		return False
	ex = u32.GetWindowLongPtrW(h, -20)
	u32.SetWindowLongPtrW(h, -20, ex | 0x08000000 | 0x80 | 0x20)   # NOACTIVATE | TOOLWINDOW | TRANSPARENT
	u32.ShowWindow(h, 0)
	S.label_hwnd = h
	S.label_text = None
	return True


def _cancel_timer():
	S = state()
	if S.timer:
		u32.KillTimer(None, S.timer)
	S.timer = 0
	S.pending = None


def _on_timer(hwnd, msg, tid, t):
	S = sys._nodewire
	u32.KillTimer(None, tid)
	if S.timer != tid:
		return
	S.timer = 0
	p, S.pending = S.pending, None
	if p and S.drag:
		u32.SetWindowPos(S.label_hwnd, HWND_TOPMOST, p[0], p[1], 0, 0, SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)


def show_label(text, sx, sy):
	S = state()
	if not _own(S.label_hwnd):
		return
	x, y = int(sx + LABEL_OFFSET), int(sy + LABEL_OFFSET)
	if text == S.label_text:
		if S.pending:
			S.pending = (x, y)
		else:
			u32.SetWindowPos(S.label_hwnd, HWND_TOPMOST, x, y, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
		return
	# new text: resize while hidden, let TouchDesigner redraw, then show
	t = _comp().op('labeltxt')
	w = min(LABEL_MAXW, int(t.evalTextSize(text)[0] + LABEL_PAD))
	t.par.text = text
	t.par.resolutionw = w
	t.cook(force=True)
	S.label_text = text
	_cancel_timer()
	u32.SetWindowPos(S.label_hwnd, None, 0, 0, w, LABEL_H, SWP_NOMOVE | SWP_NOACTIVATE | SWP_HIDEWINDOW)
	S.pending = (x, y)
	S.timer_proc = S.timer_proc or TIMERPROC(_on_timer)
	S.timer = u32.SetTimer(None, 0, REDRAW_MS, S.timer_proc)


def hide_label():
	S = state()
	_cancel_timer()
	if _own(S.label_hwnd):
		u32.SetWindowPos(S.label_hwnd, None, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_HIDEWINDOW)
	S.label_text = None


# ---------------------------------------------------------------- per frame

def on_frame():
	"""Keep the label window ready and the main window handle current."""
	S = state()
	prepare()
	if S.hook and (not S.tdhwnd or not u32.IsWindow(S.tdhwnd)):
		S.tdhwnd = _find_td_hwnd()
