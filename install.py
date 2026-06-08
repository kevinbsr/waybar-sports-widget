#!/usr/bin/env python3
import os
import shutil
import re
import subprocess
import sys

def print_colored(text, color_code):
    print(f"{color_code}{text}\033[0m")

C_BLUE = "\033[94m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_BOLD = "\033[1m"

def main():
    print_colored("=== Waybar Sports Widget Installer ===", C_BOLD + C_BLUE)
    
    # 1. Determine paths
    home = os.path.expanduser("~")
    waybar_dir = os.path.join(home, ".config", "waybar")
    scripts_dir = os.path.join(waybar_dir, "scripts")
    
    os.makedirs(scripts_dir, exist_ok=True)
    
    # Get current script directory (where installer is located)
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    src_sports = os.path.join(repo_dir, "scripts", "sports_widget.py")
    src_config = os.path.join(repo_dir, "scripts", "configure_widget.py")
    
    dest_sports = os.path.join(scripts_dir, "sports_widget.py")
    dest_config = os.path.join(scripts_dir, "configure_widget.py")
    
    # 2. Copy scripts
    print_colored("\nCopying scripts to Waybar directory...", C_BLUE)
    try:
        shutil.copy(src_sports, dest_sports)
        shutil.copy(src_config, dest_config)
        os.chmod(dest_sports, 0o755)
        os.chmod(dest_config, 0o755)
        print_colored("✅ Scripts copied and made executable.", C_GREEN)
    except Exception as e:
        print_colored(f"❌ Error copying scripts: {e}", C_RED)
        sys.exit(1)
        
    # 3. Update Waybar config.jsonc
    config_path = os.path.join(waybar_dir, "config.jsonc")
    if os.path.exists(config_path):
        print_colored("\nConfiguring Waybar module in config.jsonc...", C_BLUE)
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check if custom/sports-widget module is already defined
        if '"custom/sports-widget"' not in content:
            # 3a. Add module definition right before the final closing brace
            # Since JSONC can have trailing braces and comments, we find the last '}'
            # We will use regex or search from end
            last_brace_idx = content.rfind('}')
            if last_brace_idx != -1:
                module_def = ',\n  "custom/sports-widget": {\n    "exec": "~/.config/waybar/scripts/sports_widget.py",\n    "return-type": "json",\n    "interval": 30,\n    "tooltip": true,\n    "on-click": "~/.config/waybar/scripts/sports_widget.py --click"\n  }'
                content = content[:last_brace_idx] + module_def + "\n" + content[last_brace_idx:]
                print_colored("✅ Added 'custom/sports-widget' module definition.", C_GREEN)
        
        # 3b. Add module to active modules lists if not there
        # Look for "modules-right"
        modules_right_match = re.search(r'"modules-right"\s*:\s*\[([^\]]*)\]', content)
        if modules_right_match:
            list_content = modules_right_match.group(1)
            if '"custom/sports-widget"' not in list_content:
                # Add it right before clock if clock exists, else at the end
                if '"clock"' in list_content:
                    new_list_content = list_content.replace('"clock"', '"custom/sports-widget", "clock"')
                else:
                    # Append to the list
                    # Find last item in the list
                    items = list_content.strip().split(',')
                    if items and items[-1].strip():
                        items[-1] = items[-1] + ',\n    "custom/sports-widget"'
                        new_list_content = ",".join(items)
                    else:
                        new_list_content = list_content + '\n    "custom/sports-widget"'
                content = content.replace(modules_right_match.group(0), f'"modules-right": [{new_list_content}]')
                print_colored("✅ Added sports widget to active 'modules-right' bar.", C_GREEN)
                
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
    else:
        print_colored("⚠️ config.jsonc not found in ~/.config/waybar/. Please configure it manually.", C_YELLOW)
        
    # 4. Update Waybar style.css
    style_path = os.path.join(waybar_dir, "style.css")
    if os.path.exists(style_path):
        print_colored("\nConfiguring styles in style.css...", C_BLUE)
        with open(style_path, 'r', encoding='utf-8') as f:
            style_content = f.read()
            
        if "#custom-sports-widget" not in style_content:
            # Read styles to append
            append_path = os.path.join(repo_dir, "style.css.append")
            if os.path.exists(append_path):
                with open(append_path, 'r', encoding='utf-8') as f:
                    append_content = f.read()
                style_content += "\n" + append_content
                with open(style_path, 'w', encoding='utf-8') as f:
                    f.write(style_content)
                print_colored("✅ Appended widget styling to style.css.", C_GREEN)
            else:
                print_colored("⚠️ style.css.append file not found in repository.", C_YELLOW)
        else:
            print_colored("ℹ️ Style definition for #custom-sports-widget already exists in style.css.", C_BLUE)
    else:
        print_colored("⚠️ style.css not found in ~/.config/waybar/. Please configure it manually.", C_YELLOW)
        
    # 5. Launch configuration script
    print_colored("\nLaunching configuration wizard...", C_BOLD + C_BLUE)
    try:
        subprocess.run([sys.executable, dest_config])
    except KeyboardInterrupt:
        print_colored("\nSetup interrupted by user.", C_YELLOW)

if __name__ == "__main__":
    main()
