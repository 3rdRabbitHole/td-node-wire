# TD Node Wire

Connect and cut operator links in TouchDesigner by dragging with the right mouse button,
like Blender's Node Wrangler lazy connect.

| Gesture | Action |
| --- | --- |
| **Alt + right-drag** from one operator to another | Connect them |
| **Ctrl + right-drag** away from an operator | Cut one of its links, picked by direction |

- A small label next to the cursor shows what will happen while you drag (`→ level1`, `✂ in 0 ← noise1`)
- Connect: the first output goes to the first free input of the same family; when every input is
  taken, the first one is replaced
- Cut: drag left for the input side, right for the output side; up (or nearly horizontal) cuts the
  topmost link, down the bottommost. Output links are ordered by the position of the operator they
  go to. Drags shorter than 20 px cancel
- Palette components (pixelate, audioAnalysis, ...) work: a component counts as the family of its
  in/out operators
- Each action is one undo step (Ctrl+Z)
- Works while the timeline is paused
- Right-click without Alt or Ctrl, and right-click on empty space, are left to TouchDesigner

## Install

Drag [`node_wire.tox`](node_wire.tox) into the root (`/`) of your project.
The component is saved in the project file, so add it once to every project that should use it,
or put it in your startup file (Preferences > General > Startup File).

**Requirements:** Windows. Tested with TouchDesigner 2025.33230 at 100% display scaling.

## Known limits

- Windows only: it uses a low-level mouse hook (`WH_MOUSE_LL`) to catch the right button before
  TouchDesigner does
- Only the Network Editor inside the main window; floating panes are not handled
- Connect always uses the first matching output (e.g. `out1` of a component with two outputs)
- Component top/bottom links are not connected or cut
- With display scaling other than 100% the cursor label may be offset

## Source

All the logic is in [`node_wire.py`](node_wire.py), which is the text of the `node_wire` Text DAT
inside the component. To load an edited copy into a running project, run in the Textport (Alt+T):

```python
op('/node_wire/node_wire').text = open(r'<path>/node_wire.py', encoding='utf-8').read(); mod(op('/node_wire/node_wire')).install()
```

Then right-click the component and choose *Save Component .tox*.

## License

[MIT](LICENSE)

---

## 繁體中文

在 TouchDesigner 裡用右鍵拖曳來接線、切線，類似 Blender Node Wrangler 的 Lazy Connect。

| 手勢 | 動作 |
| --- | --- |
| **Alt + 右鍵拖曳**，從一個節點拖到另一個節點 | 接線 |
| **Ctrl + 右鍵拖曳**，從節點往外拖 | 依方向切掉其中一條線 |

- 拖曳時游標旁會顯示將要做的事（`→ level1`、`✂ in 0 ← noise1`）
- 接線：第一個輸出接到第一個空著、類型相同的輸入；全部接滿時取代第一個
- 切線：往左 = 輸入側、往右 = 輸出側；往上（或接近水平）切最上面一條，往下切最下面一條。
  輸出側依目標節點的上下位置排序。拖不到 20 px 取消
- 支援 palette 元件（pixelate、audioAnalysis 等），以它裡面 in / out 節點的類型判斷
- 每個動作都是一次 Ctrl+Z
- 時間軸暫停時也能用
- 沒按 Alt / Ctrl 的右鍵、在空白處的右鍵，都照常交給 TouchDesigner

**安裝：** 把 `node_wire.tox` 拖進專案的根層（`/`）。每個專案放一次，或放進啟動檔。

**需求：** Windows。在 TouchDesigner 2025.33230、100% 顯示縮放下測試過。
