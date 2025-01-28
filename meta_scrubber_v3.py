import os
import sys
import csv
from datetime import datetime
from PIL import Image, ExifTags
from PIL.ExifTags import TAGS, GPSTAGS
from tqdm import tqdm
import time
import piexif

class MetadataScrubber:
    def __init__(self):
        self.file_path = None
        self.original_metadata = {}
        self.scrubbed_options = set()
        self.clean_file_count = 0
        self.log_file = "metadata_changes.csv"
        self.latest_clean_file = None
        
    def welcome_screen(self):
        print("\n" + "="*50)
        print("Welcome to Image Metadata Scrubber")
        print("Currently supporting: JPG files")
        print("="*50 + "\n")
        
    def get_file_path(self):
        while True:
            file_path = input("\nPlease enter the path to your image file: ").strip()
            if os.path.exists(file_path):
                if file_path.lower().endswith(('.jpg', '.jpeg')):
                    self.file_path = file_path
                    return True
                else:
                    print("Error: Only JPG files are currently supported.")
            else:
                print("Error: File not found. Please try again.")

    def get_readable_exif(self, exif_dict):
        """Convert EXIF data to readable format similar to ExifTool"""
        readable_exif = {}
        if not exif_dict:
            return readable_exif

        for tag_id in exif_dict:
            try:
                tag = TAGS.get(tag_id, tag_id)
                data = exif_dict.get(tag_id)
                
                # Handle GPS data specially
                if tag == 'GPSInfo':
                    for gps_tag in data:
                        sub_tag = GPSTAGS.get(gps_tag, gps_tag)
                        sub_value = data[gps_tag]
                        readable_exif[f'GPS {sub_tag}'] = sub_value
                else:
                    readable_exif[tag] = data
            except Exception:
                continue
                
        return readable_exif

    def display_exif_tool_style(self, metadata, title="Current Metadata:"):
        """Display metadata in ExifTool style format"""
        print(f"\n{title}")
        print("-" * 50)
        for tag, value in sorted(metadata.items()):
            # Format the value based on its type
            if isinstance(value, bytes):
                formatted_value = f"[{len(value)} bytes of binary data]"
            elif isinstance(value, tuple):
                formatted_value = str(value)
            else:
                formatted_value = str(value)
            
            print(f"{tag:<30}: {formatted_value}")
        print("-" * 50)

    def extract_metadata(self):
        try:
            with Image.open(self.file_path) as img:
                exif = img._getexif()
                if exif:
                    self.original_metadata = self.get_readable_exif(exif)
                    self.display_exif_tool_style(self.original_metadata, "Original Metadata:")
                    return True
                else:
                    print("No EXIF data found in image.")
                    return False
        except Exception as e:
            print(f"Error reading metadata: {e}")
            return False

    def show_menu(self):
        while True:
            print("\nMetadata Scrubbing Options:")
            print("1. Remove Date/Time Information")
            print("2. Remove GPS Location")
            print("3. View Current Metadata")
            print("4. Compare Original vs Current Metadata")
            print("5. Quit")
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                self.scrub_metadata("datetime")
            elif choice == "2":
                self.scrub_metadata("gps")
            elif choice == "3":
                self.view_current_metadata()
            elif choice == "4":
                self.compare_metadata()
            elif choice == "5":
                print("\nThank you for using Image Metadata Scrubber!")
                sys.exit(0)
            else:
                print("\nInvalid choice. Please try again.")

    def scrub_metadata(self, metadata_type):
        try:
            print(f"\nRemoving {metadata_type} metadata...")
            progress_bar = tqdm(total=100, desc="Processing", ncols=75)
            
            # Read the image
            img = Image.open(self.file_path)
            
            # Create new exif dictionary
            exif_dict = piexif.load(img.info['exif']) if 'exif' in img.info else {'0th': {}, '1st': {}, 'Exif': {}, 'GPS': {}, 'Interop': {}}
            
            # Update progress
            for i in range(50):
                time.sleep(0.02)
                progress_bar.update(1)
            
            # Remove specific metadata
            if metadata_type == "datetime":
                date_time_tags = [piexif.ImageIFD.DateTime, piexif.ExifIFD.DateTimeOriginal, 
                                piexif.ExifIFD.DateTimeDigitized]
                for tag in date_time_tags:
                    if tag in exif_dict['0th']:
                        del exif_dict['0th'][tag]
                    if tag in exif_dict['Exif']:
                        del exif_dict['Exif'][tag]
                
            elif metadata_type == "gps":
                exif_dict['GPS'] = {}
            
            # Create new filename
            self.clean_file_count += 1
            base_name = os.path.splitext(self.file_path)[0]
            new_file = f"{base_name}_clean_{self.clean_file_count}.jpg"
            
            # Convert exif dict to bytes
            exif_bytes = piexif.dump(exif_dict)
            
            # Save new image
            img.save(new_file, "JPEG", exif=exif_bytes, quality=100)
            
            # Store the latest clean file path
            self.latest_clean_file = new_file
            
            # Update progress
            for i in range(50):
                time.sleep(0.02)
                progress_bar.update(1)
            
            progress_bar.close()
            
            # Log changes
            self.log_changes(metadata_type, new_file)
            
            print(f"\nMetadata removed successfully. New file saved as: {new_file}")
            
            # Show verification
            print("\nVerifying changes...")
            self.verify_changes(new_file, metadata_type)
            
        except Exception as e:
            print(f"Error during metadata removal: {e}")

    def verify_changes(self, new_file, metadata_type):
        """Verify that metadata was actually removed"""
        try:
            with Image.open(new_file) as img:
                exif = img._getexif()
                if exif:
                    new_metadata = self.get_readable_exif(exif)
                    
                    print("\nVerification Results:")
                    print("-" * 50)
                    
                    if metadata_type == "datetime":
                        date_tags = ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']
                        found_dates = False
                        for tag in date_tags:
                            if tag in new_metadata:
                                found_dates = True
                                print(f"Warning: {tag} still present in file!")
                        if not found_dates:
                            print("Success: All date/time information removed!")
                            
                    elif metadata_type == "gps":
                        found_gps = False
                        for tag in new_metadata:
                            if tag.startswith('GPS'):
                                found_gps = True
                                print(f"Warning: {tag} still present in file!")
                        if not found_gps:
                            print("Success: All GPS information removed!")
                    
                    print("-" * 50)
                    
                else:
                    print("Success: No EXIF data found in new file!")
                    
        except Exception as e:
            print(f"Error during verification: {e}")

    def view_current_metadata(self):
        """Display metadata of the most recent file"""
        latest_file = self.get_latest_clean_file()
        if latest_file:
            try:
                with Image.open(latest_file) as img:
                    exif = img._getexif()
                    if exif:
                        current_metadata = self.get_readable_exif(exif)
                        self.display_exif_tool_style(current_metadata)
                    else:
                        print("\nNo EXIF data found in current file.")
            except Exception as e:
                print(f"Error reading current metadata: {e}")
        else:
            print("\nNo cleaned files found.")

    def get_latest_clean_file(self):
        """Get the most recently created cleaned file"""
        if self.latest_clean_file and os.path.exists(self.latest_clean_file):
            return self.latest_clean_file
        return None

    def log_changes(self, metadata_type, new_file):
        headers = ['Timestamp', 'Original File', 'New File', 'Metadata Removed']
        file_exists = os.path.exists(self.log_file)
        
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                self.file_path,
                new_file,
                metadata_type
            ])

    def compare_metadata(self):
        """Compare original and current metadata"""
        if not self.original_metadata:
            print("\nNo original metadata available to compare.")
            return
            
        latest_file = self.get_latest_clean_file()
        if not latest_file:
            print("\nNo cleaned files found to compare.")
            return
            
        # Get current metadata from the latest clean file
        current_metadata = {}
        try:
            with Image.open(latest_file) as img:
                exif = img._getexif()
                if exif:
                    current_metadata = self.get_readable_exif(exif)
        except Exception as e:
            print(f"Error reading current metadata: {e}")
            return
            
        # Display comparison
        print("\nMetadata Comparison:")
        print("="* 90)
        print(f"{'Tag':<30} | {'Original Value':<25} | {'Current Value':<25}")
        print("=" * 90)
        
        # Get all unique tags from both metadata sets
        all_tags = sorted(set(list(self.original_metadata.keys()) | set(current_metadata.keys())))
        for tag in all_tags:
            orig_value = self.original_metadata.get(tag, "Not present")
            curr_value = current_metadata.get(tag, "Removed")
            
            # Format values for display
            orig_value = self._format_value_for_display(orig_value)
            curr_value = self._format_value_for_display(curr_value)
            
            # Determine if there's a change
            changed = orig_value != curr_value
            
            # Print with change indicator
            if changed:
                print(f"{tag:<30} | {orig_value[:25]:<25} | {curr_value[:25]:<25} *")
            else:
                print(f"{tag:<30} | {orig_value[:25]:<25} | {curr_value[:25]:<25}")
                
        print("=" * 90)
        print("* indicates changed or removed metadata")

    def _format_value_for_display(self, value):
        """Format metadata values for display"""
        if isinstance(value, bytes):
            return f"[{len(value)} bytes]"
        elif isinstance(value, tuple):
            return f"[{len(value)} values]"
        else:
            str_value = str(value)
            if len(str_value) > 25:
                return str_value[:22] + "..."
            return str_value

def main():
    scrubber = MetadataScrubber()
    scrubber.welcome_screen()
    
    if scrubber.get_file_path():
        if scrubber.extract_metadata():
            scrubber.show_menu()

if __name__ == "__main__":
    main()