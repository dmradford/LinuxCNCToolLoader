This simple ToolLoader takes Tool Libraries from Fusion360 and allows you to select the tools for LinuxCNC
Primarily designed for use with Carousel but can be used with fully manual changed machines.

In Fusion360, select the tool library you'd like to export and export it as "library.csv" into the directory containing ToolLoader.py

Inspect ToolLoader.config and ensure the values are correct, including any disabled pockets.

Launch ToolLoader.py
Blue rows are within the range of your tool changer. Rows can be drag-and-dropped to select your desired order. The order of the rows is persisted via ToolLoaderState.csv
Select the tools you would like to include in your tool.tbl file and click Export Selection. Any slots in the tool changer range that are not selected will be filled with an "Empty" tool to ensure the pocket numbering is correct.

Bonus: It displays tool images if you have them! Inside the ToolImages folder, simply put jpg files named according to the tool number (ie: the image for Tool Number 1 would be "1.jpg")

Enjoy!