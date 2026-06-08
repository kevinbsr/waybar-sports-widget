# Waybar Sports Score Widget

A beautiful, theme-integrated sports score widget for Waybar that fetches live
football (soccer) and basketball matches from the SofaScore API.

Designed to work seamlessly with **Omarchy** themes, but fully compatible with
any generic Waybar setup.

## Features

- 👥 **Preferred Teams Tracking:** Display detailed scores of your favorite teams
  directly in the status bar (e.g., `BRA 1-1 EGY` or `GSW 102-98 LAL`).
- 👁️ **Clean Waybar Mode (Auto-Hide):** Configurable option to completely hide
  the widget when none of your favorite teams are playing.
- 🚫 **Youth/Under Teams Filtering:** Intelligent regex filtering to ignore
  youth leagues or under teams (e.g., `U18`, `sub-20`, `under-23`),
  tracking only main/senior squads.
- ⏱️ **Post-Game Highlights:** Keep target game scores highlighted as detailed
  pills for exactly 15 minutes after they finish.
- 🎨 **Unified Theme Integration:** Uses your active Omarchy theme colors
  (`@accent` for favorite scores, `@color2` for active live games, `@color3` for
  scheduled games, and `@color8` for inactive fallbacks).
- 📊 **Live Stats & Scorers:** Hovering over the widget displays real-time statistics (Possession, Shots, Field Goals, Rebounds) and lists goalscorers (football) or the last basket scorer (basketball).
- 🔗 **Google Search Integration:** Click the widget in the status bar to
  automatically open a Google Search query for details on the active/prioritized
  match.

---

## Installation

You can install and configure the widget automatically with a single command:

```bash
curl -sL https://raw.githubusercontent.com/kevinbsr/waybar-sports-widget/main/install.sh | bash
```

### What the installer does

1. Copies the backend and configuration scripts to `~/.config/waybar/scripts/`.
2. Automatically registers the `"custom/sports-widget"` module inside your
   `~/.config/waybar/config.jsonc` and appends it to the active modules bar.
3. Appends the styling variables and class definitions to your `~/.config/waybar/style.css`.
4. Launches the setup wizard so you can immediately choose your favorite teams.

---

## Configuration Wizard

You can customize your tracking preferences at any time by running the setup wizard:

```bash
python3 ~/.config/waybar/scripts/configure_widget.py
```

### Options

1. **Preferred Teams:** Add or remove team names you want to follow
   (e.g., `brazil`, `flamengo`, `gsw`).
2. **Priority Events:** Add keywords for important events you want to track
   regardless of favorites (e.g., `nba finals`, `world cup`).
3. **Followed Tournaments:** Add/remove tournaments that appear in the general
   live matches tooltip.
4. **Show Only Favorites:** Toggle between:
   - **Enabled (Default):** Hides the widget completely when your teams aren't
     playing.
   - **Disabled:** Always displays sports icons (`⚽`, `🏀`, `🏆`) when there are
     active/scheduled games in your followed tournaments.
