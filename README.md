# TD Node Wire

Connect and cut operator links in TouchDesigner by dragging with the right mouse button,
like Blender's Node Wrangler lazy connect.

| Gesture | Action |
| --- | --- |
| **Alt + right-drag** from one operator to another | Connect them |
| **Ctrl + right-drag** from one operator to another | Cut every link between them |

- A small label next to the cursor shows the target while you drag (`→ level1`, `✂ → level1 (2)`)
- Connect: the first output goes to the first free input of the same family; when every input is
  taken, the first one is replaced
- Cut: removes every link between the two operators, in either direction
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
| **Ctrl + 右鍵拖曳**，從一個節點拖到另一個節點 | 切斷兩者之間所有的線 |

- 拖曳時游標旁會顯示目標（`→ level1`、`✂ → level1 (2)`）
- 接線：第一個輸出接到第一個空著、類型相同的輸入；全部接滿時取代第一個
- 切線：切斷兩個節點之間所有的連線，不分方向
- 支援 palette 元件（pixelate、audioAnalysis 等），以它裡面 in / out 節點的類型判斷
- 每個動作都是一次 Ctrl+Z
- 時間軸暫停時也能用
- 沒按 Alt / Ctrl 的右鍵、在空白處的右鍵，都照常交給 TouchDesigner

**安裝：** 把 `node_wire.tox` 拖進專案的根層（`/`）。每個專案放一次，或放進啟動檔。

**需求：** Windows。在 TouchDesigner 2025.33230、100% 顯示縮放下測試過。
