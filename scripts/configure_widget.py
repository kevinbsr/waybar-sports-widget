#!/usr/bin/env python3
import json
import os
import sys

CONFIG_PATH = os.path.expanduser("~/.config/waybar/scripts/sports_widget_config.json")

DEFAULT_CONFIG = {
    "preferred_teams": ["brazil", "flamengo", "gsw"],
    "priority_events": ["nba finals", "world cup finals"],
    "followed_tournaments": [
        "world cup", "copa do mundo", "world championship", "champions league", 
        "libertadores", "copa america", "euro", "brasileirão", "brasileirao",
        "copa do brasil", "premier league", "laliga", "serie a", "bundesliga",
        "friendlies", "friendly", "amistoso", "nba"
    ],
    "show_only_favorites": True
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Ensure all keys exist
                for k, v in DEFAULT_CONFIG.items():
                    if k not in config:
                        config[k] = v
                return config
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"\n❌ Error saving configuration: {e}")
        return False

# ANSI Color codes for rich interface
C_BLUE = "\033[94m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_BOLD = "\033[1m"
C_END = "\033[0m"

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def get_input(prompt_text):
    try:
        return input(prompt_text).strip()
    except (KeyboardInterrupt, EOFError):
        return ""

def configure_list(config, key, title, item_label):
    while True:
        clear_screen()
        print(f"{C_BOLD}{C_BLUE}=== Configuring: {title} ==={C_END}\n")
        items = config[key]
        
        if not items:
            print(f"  {C_YELLOW}(No items registered){C_END}\n")
        else:
            for idx, item in enumerate(items, 1):
                print(f"  {idx}. {C_BOLD}{item}{C_END}")
            print()
            
        print(f"{C_GREEN}[a]{C_END} Add {item_label}")
        if items:
            print(f"{C_RED}[r]{C_END} Remove {item_label}")
        print(f"{C_YELLOW}[v]{C_END} Back to main menu")
        
        choice = get_input(f"\nChoose an option: ").lower()
        
        if choice == 'a':
            new_item = get_input(f"\nEnter the name of the {item_label} to add: ").lower()
            if new_item:
                if new_item in items:
                    print(f"\n⚠️ '{new_item}' is already registered!")
                    time_sleep()
                else:
                    items.append(new_item)
                    print(f"\n✅ '{new_item}' added successfully!")
                    time_sleep()
        elif choice == 'r' and items:
            val = get_input(f"\nEnter the number or name of the {item_label} to remove: ")
            removed = False
            try:
                # Try index first
                idx = int(val) - 1
                if 0 <= idx < len(items):
                    item = items.pop(idx)
                    print(f"\n✅ '{item}' removed successfully!")
                    removed = True
                    time_sleep()
            except ValueError:
                # Try string matching
                val_lower = val.lower()
                if val_lower in items:
                    items.remove(val_lower)
                    print(f"\n✅ '{val_lower}' removed successfully!")
                    removed = True
                    time_sleep()
            if not removed:
                print(f"\n❌ {item_label.capitalize()} not found!")
                time_sleep()
        elif choice == 'v':
            break

def time_sleep():
    get_input("\nPress Enter to continue...")

def main():
    config = load_config()
    
    while True:
        clear_screen()
        print(f"{C_BOLD}{C_BLUE}=========================================={C_END}")
        print(f"{C_BOLD}{C_BLUE}⚙️  SPORTS WIDGET CONFIGURATION            {C_END}")
        print(f"{C_BOLD}{C_BLUE}=========================================={C_END}\n")
        
        print(f"1. 👥 {C_BOLD}Preferred Teams{C_END} (Displays full score in the bar)")
        print(f"   {C_YELLOW}Current:{C_END} {', '.join(config['preferred_teams']) if config['preferred_teams'] else 'None'}\n")
        
        print(f"2. 🏆 {C_BOLD}Priority Events{C_END} (Displays score even if not a favorite team)")
        print(f"   {C_YELLOW}Current:{C_END} {', '.join(config['priority_events']) if config['priority_events'] else 'None'}\n")
        
        print(f"3. 📅 {C_BOLD}Followed Tournaments{C_END} (Filters games in the tooltip)")
        print(f"   {C_YELLOW}Current:{C_END} {', '.join(config['followed_tournaments']) if config['followed_tournaments'] else 'None'}\n")
        
        show_fav_str = f"{C_GREEN}Enabled{C_END} (hides widget when no favorite is playing)" if config.get('show_only_favorites', True) else f"{C_RED}Disabled{C_END} (shows general sports icons for active leagues)"
        print(f"4. 👁️  {C_BOLD}Show Only Favorites{C_END}")
        print(f"   {C_YELLOW}Current:{C_END} {show_fav_str}\n")
        
        print("------------------------------------------")
        print(f"{C_GREEN}[s]{C_END} Save and Exit")
        print(f"{C_RED}[q]{C_END} Exit without Saving")
        
        choice = get_input(f"\nChoose an option: ").lower()
        
        if choice == '1':
            configure_list(config, "preferred_teams", "Preferred Teams", "team")
        elif choice == '2':
            configure_list(config, "priority_events", "Priority Events", "event")
        elif choice == '3':
            configure_list(config, "followed_tournaments", "Followed Tournaments", "tournament")
        elif choice == '4':
            config['show_only_favorites'] = not config.get('show_only_favorites', True)
            status_text = "Enabled (will hide when inactive)" if config['show_only_favorites'] else "Disabled (will always show icon)"
            print(f"\n✅ Show Only Favorites set to: {status_text}")
            time_sleep()
        elif choice == 's':
            if save_config(config):
                print(f"\n{C_GREEN}✅ Configuration saved successfully!{C_END}")
                # Reload waybar
                print("🔄 Reloading Waybar...")
                os.system("omarchy restart waybar")
                time_sleep()
                break
        elif choice == 'q':
            confirm = get_input("\nAre you sure you want to exit without saving? (y/n): ").lower()
            if confirm == 'y':
                print(f"\n{C_RED}❌ Configuration discarded.{C_END}")
                time_sleep()
                break

if __name__ == "__main__":
    main()
