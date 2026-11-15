# TD Node Wire

**English** | [繁體中文](README.zh-TW.md)

Connect and cut operator links in TouchDesigner by dragging with the right mouse button,
like Blender's Node Wrangler lazy connect.

| Gesture | Action |
| --- | --- |
| **Alt + right-drag** from one operator to another | Connect them |
| **Ctrl + right-drag** away from an operator | Cut one of its links, picked by direction |

- A small label next to the cursor shows what will happen while you drag (`→ level1`, `✂ in 0 ← noise1`)
- Connect: the first output goes to the first free input of the same family; when every input is
  taken, the first one is replaced
- Cut: the drag direction picks one link of the operator you start on
  - **Up-left**: the topmost input link
  - **Down-left**: the bottommost input link
  - **Up-right**: the topmost output link
  - **Down-right**: the bottommost output link
  - A nearly horizontal drag (within 20° of horizontal) counts as **up-left** or **up-right**
  - Output links are ordered top to bottom by the operator they go to
  - Drags shorter than 10 px cancel
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
