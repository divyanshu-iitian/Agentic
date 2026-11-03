---
name: drawing
description: Draw pictures in Microsoft Paint or any canvas app with the mouse.
triggers:
  - draw
  - paint
  - sketch
  - mspaint
  - ms paint
  - drawing
---

1. Open Paint: `desktop_open_app` with name `mspaint`.
2. Maximize it: `desktop_window` with title `Paint` and action `maximize`.
3. Call `desktop_ui_tree` with window `Paint`. Find the canvas: usually the
   largest Pane, Image, or Custom element in the middle of the window (often
   named like "Canvas" or "Drawing area"). Note its [id].
4. Click the `Brushes` (or `Pencil`) tool by its [id] before drawing. If the
   Select tool is active (for example after Ctrl+A), strokes only make
   selections. Pick a color by clicking its ListItem, such as "Red".
5. Plan the picture as simple shapes on a 0-1000 grid, where (0,0) is the top-left
   of the canvas and (1000,1000) the bottom-right. Example house with sun:
   - body: rect x=300 y=450 w=400 h=350
   - roof: polygon [[260,450],[500,250],[740,450]]
   - door: rect x=460 y=620 w=80 h=180
   - window: rect x=340 y=520 w=90 h=80
   - sun: circle cx=850 cy=180 r=80
   - ground: line [[0,800],[1000,800]]
6. Call `desktop_draw` once with all the shapes and `element` set to the canvas id.
7. Verify with `desktop_screenshot` if you can see images; otherwise report the
   shapes you drew. Do not save or close the file unless the user asked.
