#!/usr/bin/env python3
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
import subprocess

# Special flag emojis for countries/entities where simple ISO 3166-1 alpha-2 mapping is not enough
SPECIAL_COUNTRY_FLAGS = {
    "england": "🏴\u200d󠁧\u200d󠁢\u200d󠁥\u200d󠁮\u200d󠁧\u200d󠁿",
    "scotland": "🏴\u200d󠁧\u200d󠁢\u200d󠁳\u200d󠁣\u200d󠁴\u200d󠁿",
    "wales": "🏴\u200d󠁧\u200d󠁢\u200d\ud83c\uddfc\ud83c\uddf1\ud83c\uddf3\ud83c\uddf9󠁿",
    "northern ireland": "🏴\u200d󠁧\u200d󠁢\u200d󠁮\u200d󠁩\u200d󠁗\u200d󠁿",
    "kosovo": "🇽🇽",
    "brazil": "🇧🇷",
    "egypt": "🇪🇬",
    "usa": "🇺🇸",
    "lakers": "🏀",
    "warriors": "🏀",
}

# Nerd Font icons for Waybar
ICON_SOCCER = "\uf1e3"
ICON_BASKETBALL = "\ued5d"
ICON_TROPHY = "\uf091"

# Default configuration (will be merged with config file if it exists)
CONFIG = {
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
    config_path = os.path.expanduser("~/.config/waybar/scripts/sports_widget_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                for k in CONFIG:
                    if k in loaded:
                        CONFIG[k] = loaded[k]
        except Exception:
            pass

def get_clean_code(team):
    name = team.get("name", "")
    code = team.get("nameCode", "")
    
    name_lower = name.lower()
    if "brazil" in name_lower or "brasil" in name_lower:
        return "BRA"
    if "flamengo" in name_lower:
        return "FLA"
    if "warriors" in name_lower or "golden state" in name_lower:
        return "GSW"
    if "united states" in name_lower or "usa" in name_lower:
        return "USA"
    if "egypt" in name_lower:
        return "EGY"
        
    clean_name = name
    for suffix in [" u18", " u20", " u23", " sub-18", " sub-20", " sub-23", " sub 18", " sub 20", " sub 23", " u-18", " u-20", " u-23"]:
        if suffix in clean_name.lower():
            idx = clean_name.lower().find(suffix)
            clean_name = clean_name[:idx].strip()
            
    if code and len(code) == 3:
        if not (code.endswith("UU") or code.endswith("18") or code.endswith("20")):
            return code.upper()
            
    words = clean_name.split()
    if len(words) >= 1:
        first_word = words[0].upper()
        if first_word in ["BRAZIL", "BRASIL"]:
            return "BRA"
        if first_word == "ARGENTINA":
            return "ARG"
        if first_word == "GERMANY":
            return "GER"
        if first_word == "SPAIN":
            return "ESP"
        return first_word[:3]
        
    return code.upper() if code else "TBD"

def get_flag(event_team):
    country_info = event_team.get("country", {})
    alpha2 = country_info.get("alpha2")
    name = country_info.get("name", "").lower()
    
    if name in SPECIAL_COUNTRY_FLAGS:
        return SPECIAL_COUNTRY_FLAGS[name]
    
    if alpha2:
        if len(alpha2) == 2:
            return "".join(chr(127397 + ord(c)) for c in alpha2.upper())
            
    team_name = event_team.get("name", "").lower()
    for key, flag in SPECIAL_COUNTRY_FLAGS.items():
        if key in team_name:
            return flag
            
    return "⚽"

def fetch_json(url):
    try:
        cmd = [
            "curl", "-s", "--max-time", "5",
            "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "-H", "Accept-Language: en-US,en;q=0.9",
            url
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not res.stdout.strip():
            return None
        return json.loads(res.stdout)
    except Exception:
        return None

def get_live_minute(event, sport):
    status = event.get("status", {})
    desc = status.get("description", "")
    status_type = status.get("type", "")
    status_code = status.get("code")
    
    if status_type != "inprogress":
        return desc
        
    if sport == "football":
        if status_code == 31 or desc.lower() in ["halftime", "intervalo", "half-time"]:
            return "Halftime"
            
        t = event.get("time", {})
        start = t.get("currentPeriodStartTimestamp")
        initial = t.get("initial", 0)
        
        if start:
            now = int(time.time())
            elapsed = (now - start) + initial
            minute = elapsed // 60
            
            if "1st half" in desc.lower() or "1º tempo" in desc.lower():
                if minute > 45:
                    return f"45+{minute - 45}'"
                return f"{max(0, minute)}'"
            elif "2nd half" in desc.lower() or "2º tempo" in desc.lower():
                if minute > 90:
                    return f"90+{minute - 90}'"
                return f"{max(45, minute)}'"
                
            return f"{max(0, minute)}'"
            
    elif sport == "basketball":
        t = event.get("time", {})
        played = t.get("played")
        period_length = t.get("periodLength")
        if played is not None and period_length is not None:
            q_match = re.search(r"(\d+)", desc)
            if q_match:
                q = int(q_match.group(1))
                current_quarter_played = max(0, played - (q - 1) * period_length)
                remaining = max(0, period_length - current_quarter_played)
            elif "overtime" in desc.lower():
                ot_len = t.get("overtimeLength", 300)
                prev_played = 4 * period_length
                current_ot_played = max(0, played - prev_played)
                remaining = max(0, ot_len - current_ot_played)
            else:
                remaining = max(0, period_length - played)
                
            mins = remaining // 60
            secs = remaining % 60
            return f"{desc} ({mins}:{secs:02d})"
        return desc
        
    return desc

def is_under_team(team_obj):
    name = team_obj.get("name", "").lower()
    short_name = team_obj.get("shortName", "").lower()
    # Matches u15-u23, sub-15 to sub-23, under-15 to under-23 (with optional spaces/hyphens)
    pattern = r"\b(u|sub|under)[-\s]?(1[5-9]|2[0-3])\b"
    if re.search(pattern, name) or re.search(pattern, short_name):
        return True
    return False

def is_target_match(event, sport):
    home = event.get("homeTeam", {})
    away = event.get("awayTeam", {})
    
    # Exclude under/youth teams
    if is_under_team(home) or is_under_team(away):
        return None
        
    home_name = home.get("name", "").lower()
    away_name = away.get("name", "").lower()
    home_short = home.get("shortName", "").lower()
    away_short = away.get("shortName", "").lower()
    
    tournament = event.get("tournament", {})
    tournament_name = tournament.get("name", "").lower()
    
    # 1. Preferred teams
    for team in CONFIG["preferred_teams"]:
        team = team.lower()
        if team == "brazil" or team == "brasil":
            is_brazil = home_name in ["brazil", "brasil"] or away_name in ["brazil", "brasil"]
            is_national = home.get("national") is True or away.get("national") is True
            if is_brazil and is_national:
                return "brazil"
        else:
            if team in home_name or team in away_name or team in home_short or team in away_short:
                return team

    # 2. Priority events
    for event_keyword in CONFIG["priority_events"]:
        event_keyword = event_keyword.lower()
        if "nba finals" in event_keyword:
            round_name = event.get("roundInfo", {}).get("name", "").lower()
            if sport == "basketball" and "nba" in tournament_name and ("final" in tournament_name or "final" in event.get("stage_name", "").lower() or "final" in round_name or "final" in event.get("status", {}).get("description", "").lower()):
                return "nba_finals"
        elif "world cup finals" in event_keyword or "copa do mundo final" in event_keyword:
            round_name = event.get("roundInfo", {}).get("name", "").lower()
            if sport == "football" and ("world cup" in tournament_name or "copa do mundo" in tournament_name) and ("final" in tournament_name or "final" in event.get("stage_name", "").lower() or "final" in round_name or "final" in event.get("status", {}).get("description", "").lower()):
                return "worldcup_finals"
        else:
            category_name = tournament.get("category", {}).get("name", "").lower()
            if event_keyword in tournament_name or event_keyword in category_name:
                return event_keyword
            
    return None

def is_tournament_followed(event):
    if not CONFIG["followed_tournaments"]:
        return True
        
    t_name = event.get("tournament", {}).get("name", "").lower()
    c_name = event.get("tournament", {}).get("category", {}).get("name", "").lower()
    
    for term in CONFIG["followed_tournaments"]:
        term = term.lower()
        if term in t_name or term in c_name:
            return True
    return False

def fetch_statistics(event_id, sport):
    url = f"https://api.sofascore.com/api/v1/event/{event_id}/statistics"
    data = fetch_json(url)
    if not data or "statistics" not in data:
        return None
    
    stats_list = data["statistics"]
    all_period_stats = None
    for s in stats_list:
        if s.get("period") == "ALL":
            all_period_stats = s
            break
            
    if not all_period_stats and stats_list:
        all_period_stats = stats_list[0]
        
    if not all_period_stats:
        return None
        
    lines = []
    
    if sport == "football":
        possession_home = None
        possession_away = None
        shots_home = None
        shots_away = None
        
        for group in all_period_stats.get("groups", []):
            for item in group.get("statisticsItems", []):
                name = item.get("name", "").lower()
                if "possession" in name:
                    possession_home = item.get("home")
                    possession_away = item.get("away")
                elif "total shots" in name:
                    shots_home = item.get("home")
                    shots_away = item.get("away")
                    
        if possession_home or shots_home:
            lines.append("<b>Statistics:</b>")
            if possession_home:
                lines.append(f"• Possession: {possession_home} - {possession_away}")
            if shots_home:
                lines.append(f"• Shots: {shots_home} - {shots_away}")
                
    elif sport == "basketball":
        fg_home = None
        fg_away = None
        three_home = None
        three_away = None
        rebounds_home = None
        rebounds_away = None
        
        for group in all_period_stats.get("groups", []):
            for item in group.get("statisticsItems", []):
                name = item.get("name", "").lower()
                if "field goals" in name:
                    fg_home = item.get("home")
                    fg_away = item.get("away")
                elif "3-pointers" in name or "three points" in name:
                    three_home = item.get("home")
                    three_away = item.get("away")
                elif "rebounds" in name:
                    rebounds_home = item.get("home")
                    rebounds_away = item.get("away")
                    
        if fg_home or three_home or rebounds_home:
            lines.append("<b>Statistics:</b>")
            if fg_home:
                lines.append(f"• Field goals: {fg_home} - {fg_away}")
            if three_home:
                lines.append(f"• 3-Pointers: {three_home} - {three_away}")
            if rebounds_home:
                lines.append(f"• Rebounds: {rebounds_home} - {rebounds_away}")
                
    return "\n".join(lines) if lines else None

def fetch_incidents_details(event_id, sport, home_name, away_name):
    url = f"https://api.sofascore.com/api/v1/event/{event_id}/incidents"
    data = fetch_json(url)
    if not data or "incidents" not in data:
        return None
        
    incidents = data["incidents"]
    if not incidents:
        return None
        
    if sport == "football":
        home_goals = []
        away_goals = []
        
        for inc in reversed(incidents):
            if inc.get("incidentType") == "goal":
                player_name = inc.get("player", {}).get("name", "Unknown")
                time_min = inc.get("time", 0)
                added = inc.get("addedTime")
                time_str = f"{time_min}+{added}" if added and added != 999 else f"{time_min}"
                
                inc_class = inc.get("incidentClass", "")
                suffix = ""
                if inc_class == "penalty":
                    suffix = " (pen.)"
                elif inc_class == "ownGoal":
                    suffix = " (o.g.)"
                    
                goal_str = f"{player_name} {time_str}'{suffix}"
                
                if inc.get("isHome"):
                    home_goals.append(goal_str)
                else:
                    away_goals.append(goal_str)
                    
        lines = []
        if home_goals or away_goals:
            lines.append("<b>Goals:</b>")
            if home_goals:
                lines.append(f"• {home_name}: {', '.join(home_goals)}")
            if away_goals:
                lines.append(f"• {away_name}: {', '.join(away_goals)}")
        return "\n".join(lines) if lines else None
        
    elif sport == "basketball":
        for inc in incidents:
            if inc.get("incidentType") == "goal":
                player_name = inc.get("player", {}).get("name", "Unknown")
                inc_class = inc.get("incidentClass", "")
                
                pt_str = ""
                if inc_class == "onePoint":
                    pt_str = " (1pt)"
                elif inc_class == "twoPoints":
                    pt_str = " (2pts)"
                elif inc_class == "threePoints":
                    pt_str = " (3pts)"
                    
                is_home = inc.get("isHome")
                side = home_name if is_home else away_name
                
                return f"🏀 <b>Last basket:</b> {player_name}{pt_str} ({side})"
                
    return None

def get_demo_match(demo_type):
    if demo_type == "flamengo":
        return {
            "text": "FLA 2-1 VAS",
            "tooltip": (
                "<b>🏆 Copa do Brasil</b>\n"
                "────────────────────────\n"
                "<b>Flamengo</b>  2 - 1  <b>Vasco da Gama</b>\n"
                "<i>Game time: 70'</i>\n\n"
                "<b>Statistics:</b>\n"
                "• Possession: FLA (55%), VAS (45%)\n"
                "• Shots on target:  FLA (12), VAS (8)\n"
                "────────────────────────\n"
                "<i>(Demo Mode / Flamengo)</i>"
            ),
            "class": "live-target",
            "percentage": 100
        }
    elif demo_type == "gsw":
        return {
            "text": "GSW 102-98 LAL",
            "tooltip": (
                "<b>🏆 NBA Regular Season</b>\n"
                "────────────────────────\n"
                "<b>GSW Warriors</b>  102 - 98  <b>LA Lakers</b>\n"
                "<i>Game time: 4th Quarter</i>\n\n"
                "<b>Statistics:</b>\n"
                "• Field goals: GSW 38/80 (47%) - LAL 35/82 (42%)\n"
                "• 3-Pointers: GSW 14/35 (40%) - LAL 10/30 (33%)\n"
                "• Rebounds: GSW (44) - LAL (41)\n"
                "────────────────────────\n"
                "<i>(Demo Mode / Warriors)</i>"
            ),
            "class": "live-target",
            "percentage": 100
        }
    elif demo_type == "nba":
        return {
            "text": "GSW 115-110 BOS",
            "tooltip": (
                "<b>🏆 NBA Finals - Game 7</b>\n"
                "────────────────────────\n"
                "<b>GSW Warriors</b>  115 - 110  <b>Boston Celtics</b>\n"
                "<i>Game time: 4th Quarter</i>\n\n"
                "<b>Statistics:</b>\n"
                "• Field goals: GSW 42/85 (49%) - BOS 40/88 (45%)\n"
                "• 3-Pointers: GSW 16/32 (50%) - BOS 12/34 (35%)\n"
                "────────────────────────\n"
                "<i>(Demo Mode / NBA Finals)</i>"
            ),
            "class": "live-target",
            "percentage": 100
        }
    elif demo_type == "worldcup":
        return {
            "text": "BRA 2-1 FRA",
            "tooltip": (
                "<b>🏆 World Cup - Final</b>\n"
                "────────────────────────\n"
                "<b>Brazil</b>  2 - 1  <b>France</b>\n"
                "<i>Game time: 85'</i>\n\n"
                "<b>Statistics:</b>\n"
                "• Possession: BRA (52%), FRA (48%)\n"
                "• Shots on target:  BRA (9), FRA (7)\n"
                "────────────────────────\n"
                "<i>(Demo Mode / World Cup Final)</i>"
            ),
            "class": "live-target",
            "percentage": 100
        }
    else: # default demo (brazil)
        return {
            "text": "BRA 1-1 EGY",
            "tooltip": (
                "<b>🏆 International Friendlies</b>\n"
                "────────────────────────\n"
                "<b>Brazil</b>  1 - 1  <b>Egypt</b>\n"
                "<i>Game time: 15'</i>\n\n"
                "<b>Statistics:</b>\n"
                "• Possession: BRA (61%), EGY (39%)\n"
                "• Shots on target:  BRA (1), EGY (2)\n"
                "────────────────────────\n"
                "<i>(Demo Mode / Brazilian National Team)</i>"
            ),
            "class": "live-target",
            "percentage": 100
        }

def get_match_score(event):
    score = 0
    home = event.get("homeTeam", {})
    away = event.get("awayTeam", {})
    tournament = event.get("tournament", {})
    tournament_name = tournament.get("name", "").lower()
    category = tournament.get("category", {})
    category_name = category.get("name", "").lower()
    
    home_name = home.get("name", "").lower()
    away_name = away.get("name", "").lower()
    
    # Preferred teams priority
    for team in CONFIG["preferred_teams"]:
        team = team.lower()
        if team in home_name or team in away_name:
            score += 5000
            
    # Priority events priority
    for ev in CONFIG["priority_events"]:
        ev = ev.lower()
        if ev in tournament_name or ev in category_name:
            score += 2000
            
    # Followed tournaments priority
    for t in CONFIG["followed_tournaments"]:
        t = t.lower()
        if t in tournament_name or t in category_name:
            score += 500
            
    # Status priority
    status_type = event.get("status", {}).get("type", "")
    if status_type == "inprogress":
        score += 1000
        
    return score

CACHE_PATH = os.path.expanduser("~/.config/waybar/scripts/sports_widget_cache.json")
SCHED_CACHE_PATH = os.path.expanduser("~/.config/waybar/scripts/sports_widget_sched_cache.json")

def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "finished_matches" not in data:
                    data["finished_matches"] = {}
                if "last_live_target_ids" not in data:
                    data["last_live_target_ids"] = []
                return data
        except Exception:
            pass
    return {"finished_matches": {}, "last_live_target_ids": []}

def save_cache(cache):
    try:
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def invalidate_sched_cache():
    if os.path.exists(SCHED_CACHE_PATH):
        try:
            os.remove(SCHED_CACHE_PATH)
        except Exception:
            pass

def fetch_today_events_cached():
    current_time = int(time.time())
    if os.path.exists(SCHED_CACHE_PATH):
        try:
            with open(SCHED_CACHE_PATH, 'r', encoding='utf-8') as f:
                cached = json.load(f)
                # Cache for 5 minutes (300 seconds)
                if current_time - cached.get("timestamp", 0) < 300:
                    return cached.get("events_fb", []), cached.get("events_bb", [])
        except Exception:
            pass
            
    today_str = datetime.now().strftime("%Y-%m-%d")
    events_fb = (fetch_json(f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{today_str}") or {}).get("events", [])
    events_bb = (fetch_json(f"https://api.sofascore.com/api/v1/sport/basketball/scheduled-events/{today_str}") or {}).get("events", [])
    
    if not events_fb and not events_bb:
        return [], []

    try:
        with open(SCHED_CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": current_time,
                "events_fb": events_fb,
                "events_bb": events_bb
            }, f, ensure_ascii=False)
    except Exception:
        pass
        
    return events_fb, events_bb

def cleanup_cache(cache):
    current_time = int(time.time())
    to_delete = []
    for match_id, info in cache.get("finished_matches", {}).items():
        if current_time - info.get("end_time", 0) > 86400:  # 24 hours
            to_delete.append(match_id)
    for match_id in to_delete:
        del cache["finished_matches"][match_id]

def main():
    load_config()
    cache = load_cache()
    current_time = int(time.time())
    
    # Check for click action
    if "--click" in sys.argv:
        # Fetch live matches to find active one
        live_fb = fetch_json("https://api.sofascore.com/api/v1/sport/football/events/live") or {}
        live_bb = fetch_json("https://api.sofascore.com/api/v1/sport/basketball/events/live") or {}
        events_fb = live_fb.get("events", [])
        events_bb = live_bb.get("events", [])
        
        all_live = []
        for e in events_fb:
            if e.get("status", {}).get("type") == "inprogress":
                all_live.append((e, "football"))
        for e in events_bb:
            if e.get("status", {}).get("type") == "inprogress":
                all_live.append((e, "basketball"))
                
        # Filter
        live_events = []
        for event, sport in all_live:
            if is_target_match(event, sport) or is_tournament_followed(event):
                live_events.append((event, sport))
                
        # Find prioritized match
        target_live = None
        for event, sport in live_events:
            if is_target_match(event, sport):
                target_live = event
                break
                
        if target_live:
            home_name = target_live.get("homeTeam", {}).get("name", "")
            away_name = target_live.get("awayTeam", {}).get("name", "")
            query_text = f"{home_name} vs {away_name}"
        else:
            # Check recently finished target match from cache
            recently_finished = []
            for match_id, info in cache.get("finished_matches", {}).items():
                if current_time - info.get("end_time", 0) < 900:
                    recently_finished.append(info)
            if recently_finished:
                recently_finished.sort(key=lambda x: x["end_time"], reverse=True)
                target_finished = recently_finished[0]
                query_text = f"{target_finished['home_name']} vs {target_finished['away_name']}"
            elif live_events:
                home_name = live_events[0][0].get("homeTeam", {}).get("name", "")
                away_name = live_events[0][0].get("awayTeam", {}).get("name", "")
                query_text = f"{home_name} vs {away_name}"
            else:
                # Check scheduled
                events_fb_today, events_bb_today = fetch_today_events_cached()
                
                all_today = []
                for e in events_fb_today:
                    all_today.append((e, "football"))
                for e in events_bb_today:
                    all_today.append((e, "basketball"))
                    
                today_events = []
                for event, sport in all_today:
                    if is_target_match(event, sport) or is_tournament_followed(event):
                        today_events.append((event, sport))
                        
                if today_events:
                    today_events.sort(key=lambda x: get_match_score(x[0]), reverse=True)
                    home_name = today_events[0][0].get("homeTeam", {}).get("name", "")
                    away_name = today_events[0][0].get("awayTeam", {}).get("name", "")
                    query_text = f"{home_name} vs {away_name}"
                else:
                    query_text = "world cup"
                    
        # Open in default browser
        quoted = urllib.parse.quote(query_text)
        os.system(f"xdg-open 'https://www.google.com/search?q={quoted}' >/dev/null 2>&1")
        return

    # Check for demo mode
    for arg in sys.argv:
        if arg.startswith("--demo"):
            demo_type = arg.split("=")[1] if "=" in arg else "brazil"
            print(json.dumps(get_demo_match(demo_type)))
            return

    # 1. Fetch live matches for football and basketball
    live_fb = fetch_json("https://api.sofascore.com/api/v1/sport/football/events/live") or {}
    live_bb = fetch_json("https://api.sofascore.com/api/v1/sport/basketball/events/live") or {}
    
    events_fb = live_fb.get("events", [])
    events_bb = live_bb.get("events", [])
    
    all_live = []
    for e in events_fb:
        if e.get("status", {}).get("type") == "inprogress":
            all_live.append((e, "football"))
            
    for e in events_bb:
        if e.get("status", {}).get("type") == "inprogress":
            all_live.append((e, "basketball"))

    # Apply filtering (only target matches or followed tournaments)
    live_events = []
    for event, sport in all_live:
        if is_target_match(event, sport) or is_tournament_followed(event):
            live_events.append((event, sport))

    # 2. Check if a target match is live
    target_live = None
    target_type = None
    target_sport = None
    
    for event, sport in live_events:
        t_type = is_target_match(event, sport)
        if t_type:
            target_live = event
            target_type = t_type
            target_sport = sport
            break

    # Cache transition detection logic:
    current_live_target_ids = []
    if target_live:
        current_live_target_ids = [str(target_live.get("id"))]
    else:
        for event, sport in live_events:
            if is_target_match(event, sport):
                current_live_target_ids.append(str(event.get("id")))

    transition_detected = False
    for prev_id in cache.get("last_live_target_ids", []):
        if prev_id not in current_live_target_ids:
            transition_detected = True
            break

    if transition_detected:
        invalidate_sched_cache()

    cache["last_live_target_ids"] = current_live_target_ids
    save_cache(cache)

    # 3. If a live target match is live, show detailed score in the pill!
    if target_live:
        home = target_live.get("homeTeam", {})
        away = target_live.get("awayTeam", {})
        home_code = get_clean_code(home)
        away_code = get_clean_code(away)
        
        home_goals = target_live.get("homeScore", {}).get("current", 0)
        away_goals = target_live.get("awayScore", {}).get("current", 0)
        
        live_time = get_live_minute(target_live, target_sport)
        tournament_name = target_live.get("tournament", {}).get("name", "Match")
        
        text = f"{home_code} {home_goals}-{away_goals} {away_code}"
            
        stats_text = fetch_statistics(target_live.get("id"), target_sport)
        incidents_text = fetch_incidents_details(target_live.get("id"), target_sport, home.get("name", "Home"), away.get("name", "Away"))
        
        tooltip_lines = [
            f"<b>🏆 {tournament_name}</b>",
            "────────────────────────",
            f"<b>{home.get('name')}</b>  {home_goals} - {away_goals}  <b>{away.get('name')}</b>",
            f"<i>Game time: {live_time}</i>"
        ]
        
        if incidents_text:
            tooltip_lines.append("")
            tooltip_lines.append(incidents_text)
            
        if stats_text:
            tooltip_lines.append("")
            tooltip_lines.append(stats_text)
            
        other_matches = [(e, s) for e, s in live_events if e.get("id") != target_live.get("id")]
        if other_matches:
            tooltip_lines.append("────────────────────────")
            tooltip_lines.append("<b>Other live matches:</b>")
            for m, s in other_matches[:4]:
                m_home = m.get("homeTeam", {})
                m_away = m.get("awayTeam", {})
                m_home_goals = m.get("homeScore", {}).get("current", 0)
                m_away_goals = m.get("awayScore", {}).get("current", 0)
                m_time = get_live_minute(m, s)
                icon = ICON_SOCCER if s == "football" else ICON_BASKETBALL
                tooltip_lines.append(f"{icon} {m_home.get('shortName', m_home.get('name'))[:12]} {m_home_goals}-{m_away_goals} {m_away.get('shortName', m_away.get('name'))[:12]} ({m_time})")
                
        tooltip_lines.append("────────────────────────")
        tooltip_lines.append("<i>Click for details on Google</i>")
        
        output = {
            "text": text,
            "tooltip": "\n".join(tooltip_lines),
            "class": "live-target",
            "percentage": 100
        }
        print(json.dumps(output))
        return

    # 4. If NO target match is currently live, check for recently finished target matches!
    events_fb_today, events_bb_today = fetch_today_events_cached()
    all_today = []
    for e in events_fb_today:
        all_today.append((e, "football"))
    for e in events_bb_today:
        all_today.append((e, "basketball"))

    for event, sport in all_today:
        t_type = is_target_match(event, sport)
        if t_type and event.get("status", {}).get("type") == "finished":
            match_id = str(event.get("id"))
            if match_id not in cache["finished_matches"]:
                start_ts = event.get("startTimestamp", current_time)
                if match_id in cache.get("last_live_target_ids", []) or (current_time - start_ts < 18000):
                    end_time = current_time
                else:
                    if sport == "football":
                        t = event.get("time", {})
                        current_period_start = t.get("currentPeriodStartTimestamp")
                        injury_time_2 = t.get("injuryTime2", 0)
                        if current_period_start:
                            end_time = current_period_start + (45 + injury_time_2) * 60
                        else:
                            end_time = start_ts + 105 * 60
                    else:
                        end_time = start_ts + 130 * 60

                stats_text = fetch_statistics(event.get("id"), sport)
                home = event.get("homeTeam", {})
                away = event.get("awayTeam", {})
                incidents_text = fetch_incidents_details(event.get("id"), sport, home.get("name", "Home"), away.get("name", "Away"))
                
                home_code = get_clean_code(home)
                away_code = get_clean_code(away)
                home_goals = event.get("homeScore", {}).get("current", 0)
                away_goals = event.get("awayScore", {}).get("current", 0)
                tournament_name = event.get("tournament", {}).get("name", "Match")

                cache["finished_matches"][match_id] = {
                    "id": event.get("id"),
                    "home_code": home_code,
                    "away_code": away_code,
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "home_name": home.get("name", ""),
                    "away_name": away.get("name", ""),
                    "tournament_name": tournament_name,
                    "sport": sport,
                    "end_time": end_time,
                    "stats_text": stats_text,
                    "incidents_text": incidents_text
                }
                save_cache(cache)

    recently_finished = []
    for match_id, info in list(cache["finished_matches"].items()):
        end_time = info.get("end_time", 0)
        if current_time - end_time < 900:
            recently_finished.append(info)

    cleanup_cache(cache)
    save_cache(cache)

    if recently_finished:
        recently_finished.sort(key=lambda x: x["end_time"], reverse=True)
        target_finished = recently_finished[0]

        home_code = target_finished["home_code"]
        away_code = target_finished["away_code"]
        home_goals = target_finished["home_goals"]
        away_goals = target_finished["away_goals"]
        home_name = target_finished["home_name"]
        away_name = target_finished["away_name"]
        tournament_name = target_finished["tournament_name"]
        stats_text = target_finished["stats_text"]
        sport = target_finished["sport"]

        text = f"{home_code} {home_goals}-{away_goals} {away_code}"
        incidents_text = target_finished.get("incidents_text")

        status_label = "Final" if sport == "basketball" else "FT"
        tooltip_lines = [
            f"<b>🏆 {tournament_name} (Finished)</b>",
            "────────────────────────",
            f"<b>{home_name}</b>  {home_goals} - {away_goals}  <b>{away_name}</b>",
            f"<i>Status: {status_label}</i>"
        ]

        if incidents_text:
            tooltip_lines.append("")
            tooltip_lines.append(incidents_text)

        if stats_text:
            tooltip_lines.append("")
            tooltip_lines.append(stats_text)

        if live_events:
            tooltip_lines.append("────────────────────────")
            tooltip_lines.append("<b>Other live matches:</b>")
            for m, s in live_events[:4]:
                m_home = m.get("homeTeam", {})
                m_away = m.get("awayTeam", {})
                m_home_goals = m.get("homeScore", {}).get("current", 0)
                m_away_goals = m.get("awayScore", {}).get("current", 0)
                m_time = get_live_minute(m, s)
                icon = ICON_SOCCER if s == "football" else ICON_BASKETBALL
                tooltip_lines.append(f"{icon} {m_home.get('shortName', m_home.get('name'))[:12]} {m_home_goals}-{m_away_goals} {m_away.get('shortName', m_away.get('name'))[:12]} ({m_time})")

        tooltip_lines.append("────────────────────────")
        tooltip_lines.append("<i>Click for details on Google</i>")

        output = {
            "text": text,
            "tooltip": "\n".join(tooltip_lines),
            "class": "live-target",
            "percentage": 100
        }
        print(json.dumps(output))
        return

    # 5. If NO target match is live or recently finished:
    if CONFIG.get("show_only_favorites", True):
        # - Output an empty string/JSON to hide the widget from Waybar completely
        print(json.dumps({
            "text": "",
            "tooltip": "",
            "class": "hidden",
            "percentage": 0
        }))
        return

    # Otherwise, display general icons/scheduled matches (the fallback logic)
    if live_events:
        has_fb = any(s == "football" for _, s in live_events)
        has_bb = any(s == "basketball" for _, s in live_events)
        
        if has_fb and has_bb:
            text = ICON_TROPHY
        elif has_bb:
            text = ICON_BASKETBALL
        else:
            text = ICON_SOCCER
            
        tooltip_lines = ["<b>🏆 Live Matches</b>", "────────────────────────"]
        for m, s in live_events[:8]:
            m_home = m.get("homeTeam", {})
            m_away = m.get("awayTeam", {})
            m_home_goals = m.get("homeScore", {}).get("current", 0)
            m_away_goals = m.get("awayScore", {}).get("current", 0)
            m_time = get_live_minute(m, s)
            sport_icon = ICON_SOCCER if s == "football" else ICON_BASKETBALL
            
            tooltip_lines.append(f"{sport_icon} {m_home.get('shortName', m_home.get('name'))[:12]} {m_home_goals}-{m_away_goals} {m_away.get('shortName', m_away.get('name'))[:12]} ({m_time})")
            
        tooltip_lines.append("────────────────────────")
        tooltip_lines.append("<i>Click for details on Google</i>")
        
        output = {
            "text": text,
            "tooltip": "\n".join(tooltip_lines),
            "class": "live-general",
            "percentage": 80
        }
        print(json.dumps(output))
        return

    # 6. If no live matches, check scheduled matches for today
    today_events = []
    for event, sport in all_today:
        if is_target_match(event, sport) or is_tournament_followed(event):
            today_events.append((event, sport))
        
    if today_events:
        target_scheduled = None
        target_sport_sch = None
        target_type_sch = None
        
        for event, sport in today_events:
            t_type = is_target_match(event, sport)
            if t_type and event.get("status", {}).get("type") == "notstarted":
                target_scheduled = event
                target_sport_sch = sport
                target_type_sch = t_type
                break
                
        text = ICON_TROPHY
        
        tooltip_lines = []
        if target_scheduled:
            home = target_scheduled.get("homeTeam", {})
            away = target_scheduled.get("awayTeam", {})
            start_ts = target_scheduled.get("startTimestamp")
            match_time = datetime.fromtimestamp(start_ts).strftime("%H:%M") if start_ts else "Today"
            
            tooltip_lines.append(f"<b>⭐ Important match today! ({target_type_sch.upper()})</b>")
            tooltip_lines.append(f"➔ {home.get('name')} vs {away.get('name')} at {match_time}")
            tooltip_lines.append("────────────────────────")
            
        tooltip_lines.append("<b>🏆 Scheduled Matches Today</b>")
        tooltip_lines.append("────────────────────────")
        
        def sch_score(item):
            return get_match_score(item[0])
            
        today_events.sort(key=sch_score, reverse=True)
        
        for m, s in today_events[:8]:
            m_home = m.get("homeTeam", {})
            m_away = m.get("awayTeam", {})
            m_status = m.get("status", {})
            m_status_type = m_status.get("type", "")
            m_start_ts = m.get("startTimestamp")
            m_time = datetime.fromtimestamp(m_start_ts).strftime("%H:%M") if m_start_ts else ""
            sport_icon = ICON_SOCCER if s == "football" else ICON_BASKETBALL
            
            if m_status_type == "finished":
                m_home_goals = m.get("homeScore", {}).get("current", 0)
                m_away_goals = m.get("awayScore", {}).get("current", 0)
                suffix = "Final" if s == "basketball" else "FT"
                status_str = f"{m_home_goals}-{m_away_goals} ({suffix})"
            else:
                status_str = f"at {m_time}"
                
            tooltip_lines.append(f"{sport_icon} {m_home.get('shortName', m_home.get('name'))[:12]} vs {m_away.get('shortName', m_away.get('name'))[:12]} ➔ {status_str}")
            
        tooltip_lines.append("────────────────────────")
        tooltip_lines.append("<i>Click for details on Google</i>")
        
        output = {
            "text": text,
            "tooltip": "\n".join(tooltip_lines),
            "class": "upcoming-general",
            "percentage": 50
        }
        print(json.dumps(output))
        return

    # 7. Fallback if absolutely no events today
    print(json.dumps({
        "text": ICON_TROPHY,
        "tooltip": "<b>🏆 Sports</b>\n────────────────────────\nNo live or scheduled matches today.\n────────────────────────\n<i>Click to open Google Sports</i>",
        "class": "no-events",
        "percentage": 0
    }))
    return

if __name__ == "__main__":
    main()
