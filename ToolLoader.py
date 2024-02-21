import tkinter as tk
import re
from tkinter import ttk
from tkinter import messagebox
import csv
from PIL import Image, ImageTk
from pathlib import Path

def parse_config(config_path):
        config = {}
        with open(config_path, 'r') as file:
            for line in file:
                key, value = line.strip().split(': ')
                config[key] = value
        # Convert values to appropriate types
        config['Total Pockets'] = int(config['Total Pockets'])
        config['Disabled Pockets'] = [int(x) for x in config['Disabled Pockets'].split(',')] if config['Disabled Pockets'] else []
        config['Tool Changer Range'] = tuple(int(x) for x in config['Tool Changer Range'].split('-'))
        config['Manual Tool Range'] = tuple(int(x) for x in config['Manual Tool Range'].split('-'))
        return config

class ToolSelectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tool Selector")
        self.images_cache = {}  # Cache for Tkinter-compatible images to avoid reloading

        # Load the configuration here
        config_path = Path(__file__).parent / "ToolLoader.config"
        self.config = parse_config(config_path)

        # Initialize max_selections based on the config
        self.max_selections = self.config['Total Pockets'] - len(self.config['Disabled Pockets'])

        self.csv_data = {}

        self.load_csv(Path(__file__).parent / "library.csv")

        # Setup Treeview on the left side
        self.tree = ttk.Treeview(root, columns=("Carousel Pocket", "Tool Number", "Description", "Diameter", "Comment"), show="headings")
        self.tree.heading("Carousel Pocket", text="Carousel Pocket")
        self.tree.heading("Tool Number", text="Tool Number")
        self.tree.heading("Description", text="Description")
        self.tree.heading("Diameter", text="Diameter")
        self.tree.heading("Comment", text="Z Offset")
        self.tree.column("Carousel Pocket", width=100, anchor="center")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Initialize variables
        self.dragged_item = None
        self.disabled_pockets = []  # Assuming this is populated from the config
        
        # Bind mouse events for drag-and-drop
        self.tree.bind('<Button-1>', self.on_item_click)  # Could be adjusted for the specific behavior
        self.tree.bind('<B1-Motion>', self.on_item_drag)
        self.tree.bind('<ButtonRelease-1>', self.on_item_drop)

        # Right side container for the export button and image display
        self.right_side_container = tk.Frame(root)
        self.right_side_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Export button at the top of the right side
        self.export_button = ttk.Button(self.right_side_container, text="Export Selection", command=self.export_selection)
        self.export_button.pack(pady=20)

        # Image label below the export button in the right side container
        self.image_label = tk.Label(self.right_side_container)
        self.image_label.pack(fill=tk.BOTH, expand=True)

        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        self.populate_tree()


    def on_item_click(self, event):
        """Initiate drag only for non-disabled items."""
        item = self.tree.identify_row(event.y)
        if item and 'disabled' not in self.tree.item(item, 'tags'):
            self.dragged_item = item
        else:
            self.dragged_item = None  # Prevent dragging disabled items

    def on_item_drag(self, event):
        """Provide visual feedback during dragging or prevent dragging visually if needed."""
        # This could be expanded with visual feedback, but is not essential for basic functionality


    def on_item_drop(self, event):
        """Reorder items without changing 'Carousel Pocket' numbers or moving disabled pockets."""
        if not self.dragged_item:
            return  # No item was being dragged

        target_item = self.tree.identify_row(event.y)
        if not target_item or 'disabled' in self.tree.item(target_item, 'tags'):
            return  # Drop target is invalid or disabled

        # Get the index positions for drag start and drop target
        dragged_index = self.tree.index(self.dragged_item)
        target_index = self.tree.index(target_item)

        # Retrieve values for both items, ensuring they're treated as tuples
        dragged_values = tuple(self.tree.item(self.dragged_item)['values'])
        target_values = tuple(self.tree.item(target_item)['values'])

        # Swap tool data, keeping the carousel pocket numbers fixed
        if dragged_index < target_index:
            # Moving down
            self.tree.item(self.dragged_item, values=(dragged_values[0],) + target_values[1:])
            self.tree.item(target_item, values=(target_values[0],) + dragged_values[1:])
        else:
            # Moving up
            self.tree.item(self.dragged_item, values=(dragged_values[0],) + target_values[1:])
            self.tree.item(target_item, values=(target_values[0],) + dragged_values[1:])

        self.dragged_item = None  # Reset after drop


    def load_csv(self, file_path):
        if file_path.exists():
            with open(file_path, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                data = []
                for row in reader:
                    tool_number = int(row["Number (tool_number)"])  # Convert tool number to integer for sorting
                    data.append((tool_number, row))
                # Sort the list of tuples by the first element (tool number)
                sorted_data = sorted(data, key=lambda x: x[0])
                # Rebuild the csv_data dictionary with sorted entries
                self.csv_data = {str(item[0]): item[1] for item in sorted_data}


    def load_image(self, tool_number):
        # Attempt to load the specific tool image
        image_path = Path(__file__).parent / "ToolImages" / f"{tool_number}.jpg"
        if not image_path.exists():
            # If the specific tool image does not exist, load the default image
            image_path = Path(__file__).parent / "ToolImages" / "No_Image_Available.jpg"
        
        # Load and display the image (specific tool image or default)
        if image_path.exists():
            image = Image.open(image_path)
            image.thumbnail((300, 300))  # Resize image
            photo = ImageTk.PhotoImage(image)
            self.images_cache[tool_number] = photo  # Cache the image
            return photo
        else:
            # If for some reason the default image is also missing, return None
            return None

    def display_image_for_tool(self, tool_number):
        image = self.load_image(tool_number)  # Assuming this method returns a PhotoImage or None
        if image:
            self.image_label.config(image=image)
            self.image_label.image = image  # Keep a reference
        else:
            self.image_label.config(image='')  # Clear the image if none is found
            self.image_label.image = None

    def save_current_order(self):
        with open('ToolLoaderState.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for child in self.tree.get_children():
                tool_number = self.tree.item(child, 'values')[1]  # Adjust index if necessary
                writer.writerow([tool_number])

    def load_order_from_cache(self):
        cache_path = Path('ToolLoaderState.csv')
        if cache_path.exists():
            with open(cache_path, 'r') as csvfile:
                reader = csv.reader(csvfile)
                order = [row[0] for row in reader]  # Assuming each row contains one tool number
            return order
        else:
            return None

    def populate_tree(self):
        cached_order = self.load_order_from_cache()
        # Assuming self.config is already populated
        total_pockets = self.config['Total Pockets']
        disabled_pockets = self.config['Disabled Pockets']
        tool_changer_range_start, tool_changer_range_end = self.config['Tool Changer Range']

        pocket_number = 1
        row_number = 1
        inserted_tools = 0

        # Prepare a list of tool numbers for insertion based on cached order
        if cached_order:
                tool_numbers_for_insertion = cached_order

                # First pass: insert tools based on the cached or sorted order
                for tool_number in tool_numbers_for_insertion:
                    tool_info = self.csv_data.get(tool_number)
                    if tool_info:
                            tool_num = int(tool_number)
                            if tool_changer_range_start <= tool_num <= tool_changer_range_end:
                                while row_number in disabled_pockets:
                                    self.tree.insert("", "end", values=(row_number, "503", "Pocket Disabled", "0", "0"), tags=('disabled',))
                                    row_number += 1
                                    pocket_number = row_number
                                # Insert the tool with its pocket number
                                if pocket_number != '':
                                    self.tree.insert("", "end", values=(pocket_number, tool_number, tool_info["Description (tool_description)"],
                                                    f"{tool_info['Diameter (tool_diameter)']} {tool_info['Unit (tool_unit)']}",
                                                    tool_info.get("Comment (tool_comment)", "0")), tags=('carousel',))
                                else:
                                    self.tree.insert("", "end", values=(pocket_number, tool_number, tool_info["Description (tool_description)"],
                                                    f"{tool_info['Diameter (tool_diameter)']} {tool_info['Unit (tool_unit)']}",
                                                    tool_info.get("Comment (tool_comment)", "0")), tags=('rack',))
                                if row_number < total_pockets:
                                    row_number += 1
                                    pocket_number = row_number
                                else:
                                    pocket_number = ''
                                inserted_tools += 1

                # Fill the remaining pockets with empty values if there are any left within the total pockets range
                while row_number <= total_pockets:
                    if row_number in disabled_pockets:
                        self.tree.insert("", "end", values=(pocket_number, "503", "Pocket Disabled", "0", "0"), tags=('disabled',))
                    else:
                        self.tree.insert("", "end", values=(pocket_number, "", "", "", ""), tags=('empty',))
                    row_number += 1
                        

        else:
                # First, insert tools within the tool changer range, excluding disabled pockets
                for tool_number, tool_info in sorted(self.csv_data.items(), key=lambda x: int(x[0])):
                    tool_num = int(tool_number)
                    if tool_changer_range_start <= tool_num <= tool_changer_range_end:
                        while row_number in disabled_pockets:
                            self.tree.insert("", "end", values=(row_number, "503", "Pocket Disabled", "0", "0"), tags=('disabled',))
                            row_number += 1
                            pocket_number = row_number
                        # Insert the tool with its pocket number
                        if pocket_number != '':
                            self.tree.insert("", "end", values=(pocket_number, tool_number, tool_info["Description (tool_description)"],
                                            f"{tool_info['Diameter (tool_diameter)']} {tool_info['Unit (tool_unit)']}",
                                            tool_info.get("Comment (tool_comment)", "0")), tags=('carousel',))
                        else:
                            self.tree.insert("", "end", values=(pocket_number, tool_number, tool_info["Description (tool_description)"],
                                            f"{tool_info['Diameter (tool_diameter)']} {tool_info['Unit (tool_unit)']}",
                                            tool_info.get("Comment (tool_comment)", "0")), tags=('rack',))

                        if row_number < total_pockets:
                            row_number += 1
                            pocket_number = row_number
                        else:
                            pocket_number = ''
                        inserted_tools += 1

                # Fill the remaining pockets with empty values if there are any left within the total pockets range
                while row_number <= total_pockets:
                    if row_number in disabled_pockets:
                        self.tree.insert("", "end", values=(pocket_number, "503", "Pocket Disabled", "0", "0"), tags=('disabled',))
                    else:
                        self.tree.insert("", "end", values=(pocket_number, "", "", "", ""), tags=('empty',))
                    row_number += 1

        # Visually distinguish disabled pockets
        self.tree.tag_configure('disabled', background='indianred')
        # Optionally, configure empty pockets differently
        self.tree.tag_configure('empty', background='white')
        self.tree.tag_configure('carousel', background='skyblue')
        self.tree.tag_configure('rack', background='gainsboro')

    def load_order_from_cache(self):
        cache_path = Path('ToolLoaderState.csv')
        if cache_path.exists():
            with open(cache_path, 'r') as csvfile:
                reader = csv.reader(csvfile)
                return [row[0] for row in reader]
        return None

    def insert_tool_into_tree(self, tool_number, tool_info, pocket_number, disabled_pockets):
        # Determine if the current pocket is disabled
        is_disabled = pocket_number in disabled_pockets
        carousel_pocket = pocket_number if pocket_number <= self.config['Total Pockets'] else ""
        
        # Insert disabled pocket or tool info
        if is_disabled:
            self.tree.insert("", "end", values=(carousel_pocket, "503", "Pocket Disabled", "0", "0"), tags=('disabled',))
        else:
            self.tree.insert("", "end", values=(carousel_pocket, tool_number, tool_info["Description (tool_description)"],
                                                tool_info["Diameter (tool_diameter)"], tool_info.get("Comment (tool_comment)", "0")))

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if selected_items:
            selected_item = selected_items[0]  # Assuming single selection
            tool_number = self.tree.item(selected_item, 'values')[1]  # Adjust index based on "Tool Number" position
            
            # Load and display the image associated with the selected tool number
            self.display_image_for_tool(tool_number)

    def export_selection(self):
        # Path for the export file
        export_path = Path(__file__).parent / "tool.tbl"

        # Prepare the initial list of tools for export, defaulting to "Empty"
        total_pockets = self.config['Total Pockets']
        export_data = [("404", "Empty", "0", "0") for _ in range(total_pockets)]

        # Mark disabled pockets
        for pocket in self.config['Disabled Pockets']:
            if pocket <= total_pockets:  # Only consider disabled pockets within the total pockets range
                export_data[pocket - 1] = ("503", "Pocket Disabled", "0", "0")  # Adjust indices for 0-based indexing

        # Process selected items for export
        selected_items = self.tree.selection()
        for item in selected_items:
            # Assuming the first column in Treeview is the pocket number (1-based indexing)
            pocket_number, tool_number, description, diameter, comment = self.tree.item(item, 'values')
            pocket_index = int(pocket_number) - 1  # Convert to 0-based index
            if pocket_index < total_pockets:
                # Update the export data for the selected pocket
                diameter_value = diameter.split()[0]  # Extract numerical part of the diameter
                export_data[pocket_index] = (tool_number, description, diameter_value, comment)

        # Append tools from the Manual Tool Range
        manual_tool_range_start, manual_tool_range_end = self.config['Manual Tool Range']
        
        for tool_number, tool_info in sorted(self.csv_data.items(), key=lambda x: int(x[0])):
            print(tool_number)
            if manual_tool_range_start <= int(tool_number) <= manual_tool_range_end:
                # Ensure the tool is not already included
                if not any(tool[0] == tool_number for tool in export_data):
                    diameter_value = tool_info['Diameter (tool_diameter)'].split()[0]  # Assuming structure
                    export_data.append((tool_number, tool_info["Description (tool_description)"],
                                        diameter_value, tool_info.get("Comment (tool_comment)", "0")))

        # Write to the export file
        with open(export_path, 'w') as file:
            for tool_number, description, diameter, comment in export_data:
                # Adjust line format as needed
                line = f"T{tool_number} P{tool_number} X0 Y0 Z{comment} A0 B0 C0 U0 V0 W0 D{diameter} I0 J0 Q0 ;{description}\n"
                file.write(line)

        self.save_current_order()
        messagebox.showinfo("Export Successful", f"Tools exported successfully to {export_path.name}")

    def generate_tool_tbl(self, selected_tools, file_name):
        formatted_lines = []
        for tool in selected_tools:
            tool_number, description, diameter_unit, comment = tool
            diameter, unit = diameter_unit.rsplit(' ', 1)
            diameter = float(diameter)
            if unit == "in":
                diameter *= 25.4  # Convert inches to mm
            z_value = comment if comment else 0
            formatted_line = f"T{tool_number} P{tool_number} X0 Y0 Z{z_value} A0 B0 C0 U0 V0 W0 D{diameter:.2f} I0 J0 Q0 ;{description}"
            formatted_lines.append(formatted_line)

        with open(file_name, "w") as file:
            file.write("\n".join(formatted_lines))
        messagebox.showinfo("Success", "Tools exported successfully to tool.tbl.")

def main():
    root = tk.Tk()
    app = ToolSelectorApp(root)
    root.geometry("1200x600")  # Adjust the initial size of the window if needed
    root.mainloop()

if __name__ == "__main__":
    main()
