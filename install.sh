#!/bin/bash
set -e

# ANSI colors
BLUE="\033[94m"
GREEN="\033[92m"
YELLOW="\033[93m"
RED="\033[91m"
BOLD="\033[1m"
END="\033[0m"

echo -e "${BOLD}${BLUE}=== Waybar Sports Widget Installer ===${END}"

# Base raw URL for raw files (Change this to your actual github username/repo/branch before publishing!)
GITHUB_USER="your-username"
GITHUB_REPO="waybar-sports-widget"
GITHUB_BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/${GITHUB_USER}/${GITHUB_REPO}/${GITHUB_BRANCH}"

# Local targets
WAYBAR_DIR="$HOME/.config/waybar"
SCRIPTS_DIR="${WAYBAR_DIR}/scripts"
mkdir -p "${SCRIPTS_DIR}"

# Download scripts
echo -e "\n${BLUE}Downloading sports widget scripts...${END}"
curl -sL "${BASE_URL}/scripts/sports_widget.py" -o "${SCRIPTS_DIR}/sports_widget.py"
curl -sL "${BASE_URL}/scripts/configure_widget.py" -o "${SCRIPTS_DIR}/configure_widget.py"

chmod +x "${SCRIPTS_DIR}/sports_widget.py"
chmod +x "${SCRIPTS_DIR}/configure_widget.py"
echo -e "${GREEN}✅ Scripts downloaded and made executable.${END}"

# Configure Waybar config.jsonc
CONFIG_PATH="${WAYBAR_DIR}/config.jsonc"
if [ -f "$CONFIG_PATH" ]; then
    echo -e "\n${BLUE}Configuring Waybar module in config.jsonc...${END}"
    python3 -c "
import re
with open('$CONFIG_PATH', 'r', encoding='utf-8') as f:
    content = f.read()

# Add module definition
if '\"custom/sports-widget\"' not in content:
    last_brace_idx = content.rfind('}')
    if last_brace_idx != -1:
        module_def = ',\n  \"custom/sports-widget\": {\n    \"exec\": \"~/.config/waybar/scripts/sports_widget.py\",\n    \"return-type\": \"json\",\n    \"interval\": 30,\n    \"tooltip\": true,\n    \"on-click\": \"~/.config/waybar/scripts/sports_widget.py --click\"\n  }'
        content = content[:last_brace_idx] + module_def + '\n' + content[last_brace_idx:]
        print('✅ Added module definition.')

# Add module to active modules-right list
modules_right_match = re.search(r'\"modules-right\"\s*:\s*\[([^\]]*)\]', content)
if modules_right_match:
    list_content = modules_right_match.group(1)
    if '\"custom/sports-widget\"' not in list_content:
        if '\"clock\"' in list_content:
            new_list_content = list_content.replace('\"clock\"', '\"custom/sports-widget\", \"clock\"')
        else:
            items = list_content.strip().split(',')
            if items and items[-1].strip():
                items[-1] = items[-1] + ',\n    \"custom/sports-widget\"'
                new_list_content = ','.join(items)
            else:
                new_list_content = list_content + '\n    \"custom/sports-widget\"'
        content = content.replace(modules_right_match.group(0), f'\"modules-right\": [{new_list_content}]')
        print('✅ Added widget to modules-right bar.')

with open('$CONFIG_PATH', 'w', encoding='utf-8') as f:
    f.write(content)
"
else:
    echo -e "${YELLOW}⚠️ config.jsonc not found in ~/.config/waybar/. Please configure it manually.${END}"
fi

# Configure Waybar style.css
STYLE_PATH="${WAYBAR_DIR}/style.css"
if [ -f "$STYLE_PATH" ]; then
    echo -e "\n${BLUE}Configuring styles in style.css...${END}"
    if ! grep -q "#custom-sports-widget" "$STYLE_PATH"; then
        TEMP_APPEND=$(mktemp)
        curl -sL "${BASE_URL}/style.css.append" -o "$TEMP_APPEND"
        if [ -s "$TEMP_APPEND" ]; then
            cat "$TEMP_APPEND" >> "$STYLE_PATH"
            echo -e "${GREEN}✅ Appended widget styling to style.css.${END}"
        else
            echo -e "${YELLOW}⚠️ Failed to download style.css.append.${END}"
        fi
        rm -f "$TEMP_APPEND"
    else
        echo -e "${BLUE}ℹ️ Style definition for #custom-sports-widget already exists.${END}"
    fi
else
    echo -e "${YELLOW}⚠️ style.css not found in ~/.config/waybar/. Please configure it manually.${END}"
fi

# Launch configuration script
echo -e "\n${BOLD}${BLUE}Launching configuration wizard...${END}"
python3 "${SCRIPTS_DIR}/configure_widget.py"
