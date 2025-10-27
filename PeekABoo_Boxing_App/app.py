from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import sqlite3
import json
import os
from datetime import datetime, timedelta
import csv
import io
import shutil
from pathlib import Path

app = Flask(__name__)

# Configure app paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backup"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "media").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "sounds").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "icons").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "bootstrap").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "chartjs").mkdir(parents=True, exist_ok=True)

# Database and settings file paths
DB_PATH = DATA_DIR / "peekaboo.db"
SETTINGS_PATH = DATA_DIR / "settings.json"
BACKUP_DB_PATH = BACKUP_DIR / "peekaboo_backup.db"

# Default settings
DEFAULT_SETTINGS = {
    "training_time": "09:00",
    "timezone": "Africa/Lagos",
    "reminder_enabled": True,
    "sound_enabled": True,
    "theme": "light"
}

def load_settings():
    """Load settings from JSON file"""
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH, 'r') as f:
                settings = json.load(f)
                # Merge with defaults in case new settings were added
                return {**DEFAULT_SETTINGS, **settings}
        except json.JSONDecodeError:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Save settings to JSON file"""
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings, f, indent=4)

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with required tables"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Progress table
    c.execute('''CREATE TABLE IF NOT EXISTS progress
                 (week INTEGER, 
                  day INTEGER, 
                  fluidity INTEGER, 
                  endurance INTEGER, 
                  power INTEGER, 
                  date TEXT,
                  notes TEXT,
                  PRIMARY KEY (week, day))''')
    
    # Sessions table for tracking completion
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  week INTEGER,
                  day INTEGER,
                  completed_date TEXT,
                  duration INTEGER,
                  UNIQUE(week, day))''')
    
    conn.commit()
    conn.close()
    
    # Initialize settings file if it doesn't exist
    if not SETTINGS_PATH.exists():
        save_settings(DEFAULT_SETTINGS)

def backup_database():
    """Create a backup of the database"""
    if DB_PATH.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"peekaboo_backup_{timestamp}.db"
        shutil.copy2(DB_PATH, backup_file)
        
        # Keep only last 10 backups
        backups = sorted(BACKUP_DIR.glob("peekaboo_backup_*.db"))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                old_backup.unlink()
        
        return str(backup_file)
    return None

# Training program data
TRAINING_DATA = {
    1: {
        1: {
            "focus": "Rhythm & Form",
            "duration": "60-75 minutes",
            "description": "Introduction to peek-a-boo stance, basic head movement, and rhythm development",
            "warmup": ["Jump rope - 3 rounds of 2 minutes", "Arm circles - 2 sets of 20", "Shadow footwork - 3 minutes", "Dynamic stretching - 5 minutes"],
            "technical": ["Peek-a-boo stance hold - 3x1 min", "Slip lines (left/right) - 4 sets of 10", "Double bob & weave - 3 sets of 8", "Guard positioning drills - 5 minutes"],
            "combos": ["Slip Right → Left Hook → Right Uppercut (3x10)", "Bob → Double Jab → Right Hand (3x10)", "Weave Left → Right Hook to Body (3x10)"],
            "bagwork": ["4 rounds of 2 minutes - Focus on form", "Emphasis on tight defense between punches", "Practice peek-a-boo head position"],
            "conditioning": ["Jump squats - 3 sets of 15", "Plank punches - 3 sets of 20", "Russian twists - 3 sets of 30"],
            "recovery": ["Deep breathing - 5 minutes", "Static stretching - 10 minutes", "Foam rolling - 5 minutes"]
        },
        2: {
            "focus": "Head Movement Fundamentals",
            "duration": "60-75 minutes",
            "description": "Building defensive reflexes and slip-counter combinations",
            "warmup": ["Jump rope - 3 rounds of 2 minutes", "Neck rotations - 20 each direction", "Shadow boxing - 3 minutes", "Hip openers - 5 minutes"],
            "technical": ["Slip-slip-roll drill - 5 sets of 8", "Figure-8 head movement - 3 sets of 10", "Partner slip practice (or solo) - 4x2 min", "Defensive stance flow - 5 minutes"],
            "combos": ["Slip → Hook to Body → Hook to Head (4x8)", "Roll Under → Right Uppercut → Left Hook (4x8)", "Double Slip → Right Hand → Left Hook (4x8)"],
            "bagwork": ["5 rounds of 2 minutes - Head movement emphasis", "Move after every combination", "Keep hands high in peek-a-boo position"],
            "conditioning": ["Mountain climbers - 3 sets of 30", "Medicine ball slams - 3 sets of 15", "Bicycle crunches - 3 sets of 30"],
            "recovery": ["Cool down walk - 3 minutes", "Shoulder stretches - 5 minutes", "Meditation/breathing - 5 minutes"]
        },
        3: {
            "focus": "Power Generation from Low Position",
            "duration": "70-80 minutes",
            "description": "Developing explosive power from the crouch and generating force through legs",
            "warmup": ["Jump rope - 4 rounds of 2 minutes", "Squat pulses - 2 sets of 20", "Shadow boxing with emphasis on squat - 4 minutes", "Leg swings - 2 sets of 15 each"],
            "technical": ["Crouch to explosion drill - 5 sets of 5", "Level change practice - 4 sets of 10", "Spring-loaded stance drills - 4x2 min", "Weight transfer exercises - 5 minutes"],
            "combos": ["Crouch → Spring Up → Left Hook (4x10)", "Level Change → Double Uppercut (4x10)", "Bob → Explode → Right Hand → Left Hook (4x10)"],
            "bagwork": ["6 rounds of 2 minutes - Power focus", "Every punch from compressed position", "Feel the leg drive in every shot"],
            "conditioning": ["Box jumps - 4 sets of 12", "Explosive push-ups - 4 sets of 10", "Burpees - 3 sets of 15"],
            "recovery": ["Light stretching - 10 minutes", "Ice problem areas - 10 minutes", "Protein intake within 30 minutes"]
        },
        4: {
            "focus": "Combination Flow & Rhythm",
            "duration": "65-75 minutes",
            "description": "Linking defensive movements with offensive combinations seamlessly",
            "warmup": ["Jump rope with footwork patterns - 4x2 min", "Shadow flow sequences - 5 minutes", "Dynamic stretches - 5 minutes"],
            "technical": ["4-punch combinations from defense - 5 sets", "Flow drills: Slip-Hook-Slip-Hook - 4x2 min", "Rhythm shadowboxing - 3 rounds of 3 minutes"],
            "combos": ["Slip → Jab → Cross → Hook → Uppercut (5x6)", "Roll → Hook Body → Hook Head → Cross (5x6)", "Weave → Uppercut → Hook → Cross (5x6)"],
            "bagwork": ["5 rounds of 3 minutes - Flowing combinations", "Focus on rhythm over power", "No pause between defensive and offensive moves"],
            "conditioning": ["Jump rope intervals - 5x1 min high intensity", "Core rotation exercises - 4 sets of 20", "Shadowboxing sprints - 3x1 min all-out"],
            "recovery": ["Cool down shadowboxing - 3 minutes", "Full body stretch - 12 minutes"]
        },
        5: {
            "focus": "Sparring Simulation & Pressure",
            "duration": "75-85 minutes",
            "description": "Testing skills under pressure with continuous movement and combinations",
            "warmup": ["Extended jump rope - 5x2 min", "Full shadow round with all techniques - 3x3 min", "Dynamic warm-up - 8 minutes"],
            "technical": ["Pressure drill - advancing with defense - 4x2 min", "Counter-punching sequences - 5 sets of 8", "Distance management - 3x3 min"],
            "combos": ["Free-flowing combinations - Work all week's combos", "Defensive then offensive sequences", "Pressure fighting - constant movement"],
            "bagwork": ["8 rounds of 2 minutes - Simulated sparring", "Mix power, speed, and defense", "Constant movement and angles"],
            "conditioning": ["Heavy bag power punches - 3 sets of 30 seconds all-out", "Sprawl and box drill - 4 sets of 10", "Core finisher circuit - 8 minutes"],
            "recovery": ["Extensive stretching - 15 minutes", "Ice bath or contrast shower - 10 minutes", "Rest and nutrition planning"]
        }
    },
    2: {
        1: {
            "focus": "Speed & Snap Development",
            "duration": "65-75 minutes",
            "description": "Developing hand speed and snap while maintaining defensive posture",
            "warmup": ["Speed rope - 4x2 min", "Wrist rotations - 2 sets of 30", "Fast shadowboxing - 4 minutes", "Arm loosening exercises - 5 minutes"],
            "technical": ["Speed jab drills - 5 sets of 20", "Fast hand combinations - 4x30 seconds", "Snap-back technique practice - 5 minutes", "Hand speed ladder drills - 4 sets"],
            "combos": ["Triple Jab → Cross (5x10)", "Speed: Hook-Hook-Uppercut (5x10)", "Fast: Jab-Cross-Hook-Cross (5x10)"],
            "bagwork": ["6 rounds of 2 minutes - Speed focus", "Light gloves if available", "Focus on snap, not power"],
            "conditioning": ["Speed bag - 4x2 min (or substitute with fast punching)", "Shoulder burnout - 3 sets to failure", "Fast feet drills - 4x30 seconds"],
            "recovery": ["Arm cooldown swings - 5 minutes", "Shoulder stretches - 8 minutes", "Deep breathing - 5 minutes"]
        },
        2: {
            "focus": "Advanced Head Movement",
            "duration": "70-80 minutes",
            "description": "Complex defensive patterns and creating angles",
            "warmup": ["Jump rope - 4x2 min", "Neck strengthening - 3 sets of 15", "Shadow defense - 5 minutes", "Full body mobility - 8 minutes"],
            "technical": ["Advanced slip sequences - 5 sets of 12", "Circular head movement - 4x2 min", "Shoulder roll integration - 5 sets of 10", "Matrix-style evasion drills - 4 sets"],
            "combos": ["Slip-Roll-Slip → Uppercut-Hook (4x10)", "Circular movement → Power shots (4x10)", "Pull-counter combinations (4x10)"],
            "bagwork": ["7 rounds of 2 minutes - Maximum head movement", "Every punch preceded by defense", "Create angles before attacking"],
            "conditioning": ["Neck bridges - 3 sets of 30 seconds", "Core anti-rotation - 4 sets of 20", "Explosive medicine ball throws - 3 sets of 12"],
            "recovery": ["Neck massage/release - 5 minutes", "Upper body stretching - 10 minutes", "Meditation - 5 minutes"]
        },
        3: {
            "focus": "Body Attack Mastery",
            "duration": "70-80 minutes",
            "description": "Perfecting body punches and level changes",
            "warmup": ["Jump rope - 4x2 min with squats between rounds", "Deep squat holds - 3x45 seconds", "Shadow body punching - 5 minutes", "Hip mobility - 5 minutes"],
            "technical": ["Body shot mechanics - 5 sets of 10 each hand", "Level change drills - 5 sets of 12", "Dip and rip technique - 4x2 min", "Shovel hook practice - 5 sets of 10"],
            "combos": ["Jab Head → Double Hook Body (5x8)", "Cross → Left Hook Body → Right Uppercut Body (5x8)", "Body-Body-Head combinations (5x8)"],
            "bagwork": ["8 rounds of 2 minutes - 70% body shots", "Punish the body", "Mix levels constantly"],
            "conditioning": ["Weighted squat punches - 4 sets of 15", "Woodchoppers - 4 sets of 20", "V-ups - 4 sets of 15"],
            "recovery": ["Lower back stretches - 8 minutes", "Hip flexor release - 5 minutes", "Glute stretches - 5 minutes"]
        },
        4: {
            "focus": "Pressure Fighting",
            "duration": "75-85 minutes",
            "description": "Constant forward pressure with defense",
            "warmup": ["Aggressive jump rope - 5x2 min", "Shadow pressure fighting - 4x3 min", "Full warm-up circuit - 10 minutes"],
            "technical": ["Walk-down drills - 5x2 min", "Cut-off-the-ring footwork - 4 sets", "Pressure with defense - 5x2 min", "Relentless attack drills - 4 sets"],
            "combos": ["Jab-Cross-Hook stepping in (5x10)", "Bob-Weave advancing with power shots (5x10)", "Non-stop combination pressure (5x10)"],
            "bagwork": ["10 rounds of 2 minutes - Constant pressure", "Never stop moving forward", "Attack, defend, attack pattern"],
            "conditioning": ["Prowler push or sled drag - 5 sets of 30m", "Bear crawls - 4 sets of 20m", "Battle ropes - 4x30 seconds"],
            "recovery": ["Active recovery walk - 10 minutes", "Full body stretch - 15 minutes", "Contrast therapy if available"]
        },
        5: {
            "focus": "Week 2 Integration",
            "duration": "80-90 minutes",
            "description": "Combining all Week 2 skills in high-intensity session",
            "warmup": ["Extended warm-up - 15 minutes", "Shadow review of all techniques - 3x3 min"],
            "technical": ["Review all week's drills - 20 minutes rotating", "Free-form defensive movement - 3x3 min"],
            "combos": ["Mix all week's combinations - 10 minutes continuous", "Student choice - practice weakest combos"],
            "bagwork": ["12 rounds of 2 minutes - Everything integrated", "Speed, power, defense, pressure", "Simulated fight conditions"],
            "conditioning": ["High-intensity finisher circuit - 15 minutes", "All exercises from the week", "Maximum effort"],
            "recovery": ["Extensive cool down - 20 minutes", "Ice and nutrition", "Weekend rest earned"]
        }
    },
    3: {
        1: {
            "focus": "Counter-Punching Excellence",
            "duration": "70-80 minutes",
            "description": "Reading opponent patterns and countering effectively",
            "warmup": ["Jump rope - 4x2 min", "Reaction drills - 5 minutes", "Shadow counter-punching - 5 minutes"],
            "technical": ["Catch and counter drills - 5 sets of 10", "Pull counter technique - 4x2 min", "Anticipation exercises - 5 sets"],
            "combos": ["Slip → Counter Cross (5x10)", "Block → Hook Counter (5x10)", "Roll → Uppercut Counter (5x10)"],
            "bagwork": ["7 rounds of 2 minutes - Counter focus", "Imagine attacks coming", "Defensive then explosive counter"],
            "conditioning": ["Reaction ball drills - 4 sets", "Speed ladders - 5 sets", "Core work - 10 minutes"],
            "recovery": ["Stretching - 12 minutes", "Meditation - 5 minutes"]
        },
        2: {
            "focus": "Inside Fighting",
            "duration": "70-80 minutes",
            "description": "Mastering close-range warfare",
            "warmup": ["Jump rope - 4x2 min", "Shoulder warm-up - 5 minutes", "Close-range shadow - 5 minutes"],
            "technical": ["Clinch positioning - 5 sets", "Short punch mechanics - 5 sets of 12", "Inside leverage drills - 4x2 min"],
            "combos": ["Short hooks inside (5x12)", "Uppercuts in pocket (5x12)", "Rapid-fire body shots (5x12)"],
            "bagwork": ["8 rounds of 2 minutes - Phone booth fighting", "Stay close to bag", "All short punches"],
            "conditioning": ["Heavy bag hug and punch - 4x1 min", "Resistance band punches - 4 sets of 20", "Plank variations - 10 minutes"],
            "recovery": ["Upper body focus stretch - 15 minutes"]
        },
        3: {
            "focus": "Footwork & Angles",
            "duration": "65-75 minutes",
            "description": "Advanced footwork patterns and angle creation",
            "warmup": ["Jump rope with lateral movement - 5x2 min", "Ladder drills - 10 minutes", "Shadow with angles - 5 minutes"],
            "technical": ["Pivot drills - 5 sets of 10 each side", "Step-drag sequences - 4x2 min", "Angle creation - 5 sets"],
            "combos": ["Pivot Left → Hook (5x10)", "Step Right → Cross (5x10)", "Circle → Double Jab (5x10)"],
            "bagwork": ["6 rounds of 3 minutes - Constant angles", "Never stand still", "Hit and move"],
            "conditioning": ["Lateral bounds - 4 sets of 12", "Cone drills - 5 sets", "Agility ladder - 8 minutes"],
            "recovery": ["Leg stretching - 12 minutes", "Foam roll - 8 minutes"]
        },
        4: {
            "focus": "Power Punching Session",
            "duration": "75-85 minutes",
            "description": "Maximum force generation and knockout power",
            "warmup": ["Jump rope - 4x2 min", "Dynamic explosiveness - 8 minutes", "Power shadow - 5 minutes"],
            "technical": ["Heavy bag power drills - 5 sets of 6", "Max force technique - 4 sets", "Explosion from stance - 5 sets of 5"],
            "combos": ["Power: Cross-Hook-Cross (4x8)", "Uppercut with full power (4x8)", "Overhand right (4x8)"],
            "bagwork": ["5 rounds of 3 minutes - 100% power", "Rest 2 minutes between rounds", "Every shot maximum effort"],
            "conditioning": ["Heavy bag max punches - 5x30 seconds", "Medicine ball throws - 5 sets of 10", "Power push-ups - 4 sets of 12"],
            "recovery": ["Extended recovery - 20 minutes", "Ice shoulders - 10 minutes"]
        },
        5: {
            "focus": "Week 3 Mastery Test",
            "duration": "80-90 minutes",
            "description": "Integration and testing of all Week 3 skills",
            "warmup": ["Complete warm-up - 15 minutes"],
            "technical": ["All week's drills review - 25 minutes"],
            "combos": ["Free combination work - 15 minutes"],
            "bagwork": ["Hard sparring simulation - 12x2 min", "Use all techniques learned", "Maximal intensity"],
            "conditioning": ["Final week test circuit - 20 minutes"],
            "recovery": ["Complete recovery protocol - 25 minutes"]
        }
    },
    4: {
        1: {"focus": "Speed Endurance", "duration": "70-80 minutes", "description": "Maintaining speed through fatigue", "warmup": ["Extended cardio - 15 min"], "technical": ["High-volume speed work"], "combos": ["Fast combinations - sustained"], "bagwork": ["10 rounds speed focus"], "conditioning": ["Endurance circuit"], "recovery": ["Active recovery"]},
        2: {"focus": "Advanced Defense", "duration": "70-80 minutes", "description": "Elite defensive techniques", "warmup": ["Standard"], "technical": ["Complex defensive patterns"], "combos": ["Defense-first combinations"], "bagwork": ["8 rounds defensive"], "conditioning": ["Defensive conditioning"], "recovery": ["Standard"]},
        3: {"focus": "Combination Complexity", "duration": "75-85 minutes", "description": "Multi-punch sequences", "warmup": ["Standard"], "technical": ["Long combinations"], "combos": ["5-8 punch sequences"], "bagwork": ["Complex combo rounds"], "conditioning": ["Arm endurance"], "recovery": ["Standard"]},
        4: {"focus": "Fight Simulation", "duration": "80-90 minutes", "description": "Realistic fight scenarios", "warmup": ["Fight prep"], "technical": ["Situational drills"], "combos": ["Adaptive combinations"], "bagwork": ["Sparring style rounds"], "conditioning": ["Fight conditioning"], "recovery": ["Post-fight protocol"]},
        5: {"focus": "Week 4 Peak", "duration": "85-95 minutes", "description": "Peak performance integration", "warmup": ["Full prep"], "technical": ["All skills"], "combos": ["Everything"], "bagwork": ["Maximum rounds"], "conditioning": ["Peak circuit"], "recovery": ["Full recovery"]}
    },
    5: {
        1: {"focus": "Mental Toughness", "duration": "75-85 minutes", "description": "Pushing through barriers", "warmup": ["Standard"], "technical": ["Fatigue drills"], "combos": ["Under pressure"], "bagwork": ["Extended rounds"], "conditioning": ["Mental endurance"], "recovery": ["Mental recovery"]},
        2: {"focus": "Precision Under Fatigue", "duration": "75-85 minutes", "description": "Accuracy when tired", "warmup": ["Standard"], "technical": ["Precision drills"], "combos": ["Accurate combinations"], "bagwork": ["Target focused"], "conditioning": ["Precision conditioning"], "recovery": ["Standard"]},
        3: {"focus": "Power Endurance", "duration": "80-90 minutes", "description": "Maintaining power late", "warmup": ["Standard"], "technical": ["Power sustainability"], "combos": ["Hard combinations"], "bagwork": ["Power throughout"], "conditioning": ["Power endurance"], "recovery": ["Deep recovery"]},
        4: {"focus": "Championship Rounds", "duration": "85-95 minutes", "description": "Going the distance", "warmup": ["Extended"], "technical": ["Endurance patterns"], "combos": ["Sustained output"], "bagwork": ["15+ rounds"], "conditioning": ["Championship circuit"], "recovery": ["Extended"]},
        5: {"focus": "Week 5 Completion", "duration": "90-100 minutes", "description": "Near-peak performance", "warmup": ["Full"], "technical": ["Everything"], "combos": ["All techniques"], "bagwork": ["Maximum volume"], "conditioning": ["Peak test"], "recovery": ["Full protocol"]}
    },
    6: {
        1: {"focus": "Peak Speed", "duration": "75-85 minutes", "description": "Fastest you've ever been", "warmup": ["Speed prep"], "technical": ["Maximum speed drills"], "combos": ["Lightning fast"], "bagwork": ["Speed rounds"], "conditioning": ["Speed conditioning"], "recovery": ["Standard"]},
        2: {"focus": "Peak Power", "duration": "75-85 minutes", "description": "Hardest you've ever hit", "warmup": ["Power prep"], "technical": ["Max power drills"], "combos": ["Devastating shots"], "bagwork": ["Power display"], "conditioning": ["Power peak"], "recovery": ["Ice recovery"]},
        3: {"focus": "Peak Defense", "duration": "75-85 minutes", "description": "Untouchable movement", "warmup": ["Defense prep"], "technical": ["Elite defense"], "combos": ["Perfect defense"], "bagwork": ["Defensive mastery"], "conditioning": ["Defense stamina"], "recovery": ["Standard"]},
        4: {"focus": "Final Preparation", "duration": "80-90 minutes", "description": "Bringing it all together", "warmup": ["Complete prep"], "technical": ["All systems"], "combos": ["Complete arsenal"], "bagwork": ["Showcase rounds"], "conditioning": ["Final test"], "recovery": ["Pre-peak recovery"]},
        5: {"focus": "Graduation Day", "duration": "90-120 minutes", "description": "Demonstrate mastery of peek-a-boo style", "warmup": ["Championship warm-up"], "technical": ["Final demonstration"], "combos": ["Everything perfected"], "bagwork": ["Victory rounds"], "conditioning": ["Celebration circuit"], "recovery": ["Champion's rest"]}
    }
}

# Initialize database on startup
init_db()

@app.route('/')
def index():
    """Dashboard view"""
    conn = get_db_connection()
    progress_data = conn.execute("SELECT week, day FROM progress ORDER BY week, day").fetchall()
    conn.close()
    
    completed_sessions = {(row['week'], row['day']) for row in progress_data}
    
    return render_template('dashboard.html', 
                         weeks=range(1, 7),
                         completed_sessions=completed_sessions,
                         training_data=TRAINING_DATA)

@app.route('/splash')
def splash():
    """Splash screen"""
    return render_template('splash.html')

@app.route('/week/<int:week>/day/<int:day>')
def session(week, day):
    """Individual training session view"""
    if week not in TRAINING_DATA or day not in TRAINING_DATA[week]:
        return "Session not found", 404
    
    session_data = TRAINING_DATA[week][day]
    
    # Get existing progress
    conn = get_db_connection()
    result = conn.execute(
        "SELECT fluidity, endurance, power, notes FROM progress WHERE week=? AND day=?",
        (week, day)
    ).fetchone()
    conn.close()
    
    existing_progress = None
    if result:
        existing_progress = {
            "fluidity": result['fluidity'],
            "endurance": result['endurance'],
            "power": result['power'],
            "notes": result['notes']
        }
    
    settings = load_settings()
    
    return render_template('session.html', 
                         week=week, 
                         day=day,
                         session=session_data,
                         progress=existing_progress,
                         settings=settings)

@app.route('/save_progress', methods=['POST'])
def save_progress():
    """Save training progress"""
    data = request.json
    week = data['week']
    day = data['day']
    fluidity = data['fluidity']
    endurance = data['endurance']
    power = data['power']
    notes = data.get('notes', '')
    
    conn = get_db_connection()
    conn.execute('''INSERT OR REPLACE INTO progress 
                    (week, day, fluidity, endurance, power, date, notes) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (week, day, fluidity, endurance, power, datetime.now().isoformat(), notes))
    conn.commit()
    conn.close()
    
    # Create automatic backup
    backup_database()
    
    return jsonify({"success": True})

@app.route('/progress')
def progress():
    """Progress tracking and analytics view"""
    conn = get_db_connection()
    data = conn.execute(
        "SELECT week, day, fluidity, endurance, power, date, notes FROM progress ORDER BY week, day"
    ).fetchall()
    conn.close()
    
    # Calculate statistics
    if data:
        avg_fluidity = sum(row['fluidity'] for row in data) / len(data)
        avg_endurance = sum(row['endurance'] for row in data) / len(data)
        avg_power = sum(row['power'] for row in data) / len(data)
        total_sessions = len(data)
        
        # Calculate weekly averages
        weekly_stats = {}
        for row in data:
            week = row['week']
            if week not in weekly_stats:
                weekly_stats[week] = {'fluidity': [], 'endurance': [], 'power': []}
            weekly_stats[week]['fluidity'].append(row['fluidity'])
            weekly_stats[week]['endurance'].append(row['endurance'])
            weekly_stats[week]['power'].append(row['power'])
        
        for week in weekly_stats:
            weekly_stats[week] = {
                'fluidity': round(sum(weekly_stats[week]['fluidity']) / len(weekly_stats[week]['fluidity']), 2),
                'endurance': round(sum(weekly_stats[week]['endurance']) / len(weekly_stats[week]['endurance']), 2),
                'power': round(sum(weekly_stats[week]['power']) / len(weekly_stats[week]['power']), 2)
            }
    else:
        avg_fluidity = avg_endurance = avg_power = 0
        total_sessions = 0
        weekly_stats = {}
    
    return render_template('progress.html',
                         progress_data=data,
                         avg_fluidity=round(avg_fluidity, 2),
                         avg_endurance=round(avg_endurance, 2),
                         avg_power=round(avg_power, 2),
                         total_sessions=total_sessions,
                         weekly_stats=weekly_stats)

@app.route('/export')
def export():
    """Export options view"""
    backups = sorted(BACKUP_DIR.glob("peekaboo_backup_*.db"), reverse=True)
    backup_list = [{"name": b.name, "date": datetime.fromtimestamp(b.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")} for b in backups[:10]]
    
    return render_template('export.html', backups=backup_list)

@app.route('/export/progress_csv')
def export_progress_csv():
    """Export progress data as CSV"""
    conn = get_db_connection()
    data = conn.execute(
        "SELECT week, day, fluidity, endurance, power, date, notes FROM progress ORDER BY week, day"
    ).fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Week', 'Day', 'Fluidity', 'Endurance', 'Power', 'Date', 'Notes'])
    
    for row in data:
        writer.writerow([row['week'], row['day'], row['fluidity'], 
                        row['endurance'], row['power'], row['date'], 
                        row['notes'] or ''])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'peekaboo_progress_{datetime.now().strftime("%Y%m%d")}.csv'
    )

@app.route('/export/calendar_csv')
def export_calendar_csv():
    """Export training calendar as CSV for import into calendar apps"""
    settings = load_settings()
    training_time = settings.get('training_time', '09:00')
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Subject', 'Start Date', 'Start Time', 'End Date', 'End Time', 'Description', 'Location'])
    
    start_date = datetime.now()
    
    for week in range(1, 7):
        for day in range(1, 6):
            if week in TRAINING_DATA and day in TRAINING_DATA[week]:
                session_date = start_date + timedelta(weeks=week-1, days=day-1)
                session_data = TRAINING_DATA[week][day]
                
                # Parse duration to calculate end time
                duration_parts = session_data['duration'].split('-')
                avg_duration = int(duration_parts[0]) if duration_parts else 75
                
                date_str = session_date.strftime('%m/%d/%Y')
                end_time = (datetime.strptime(training_time, '%H:%M') + timedelta(minutes=avg_duration)).strftime('%H:%M')
                
                description = f"{session_data['description']}\n\nFocus: {session_data['focus']}"
                
                writer.writerow([
                    f'Peek-a-Boo Boxing W{week}D{day}: {session_data["focus"]}',
                    date_str,
                    training_time,
                    date_str,
                    end_time,
                    description,
                    'Training Location'
                ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'peekaboo_schedule_{datetime.now().strftime("%Y%m%d")}.csv'
    )

@app.route('/export/full_program_pdf')
def export_full_program():
    """Export complete training program as text file"""
    output = io.StringIO()
    
    output.write("PEEK-A-BOO BOXING TRAINING PROGRAM\n")
    output.write("=" * 80 + "\n\n")
    
    for week in range(1, 7):
        output.write(f"\n{'='*80}\n")
        output.write(f"WEEK {week}\n")
        output.write(f"{'='*80}\n\n")
        
        for day in range(1, 6):
            if week in TRAINING_DATA and day in TRAINING_DATA[week]:
                session = TRAINING_DATA[week][day]
                
                output.write(f"\nDAY {day}: {session['focus']}\n")
                output.write(f"{'-'*80}\n")
                output.write(f"Duration: {session['duration']}\n")
                output.write(f"Description: {session['description']}\n\n")
                
                sections = ['warmup', 'technical', 'combos', 'bagwork', 'conditioning', 'recovery']
                section_names = ['WARM-UP', 'TECHNICAL WORK', 'COMBINATIONS', 'BAG WORK', 'CONDITIONING', 'RECOVERY']
                
                for section, name in zip(sections, section_names):
                    if section in session and session[section]:
                        output.write(f"\n{name}:\n")
                        for item in session[section]:
                            output.write(f"  • {item}\n")
                
                output.write("\n" + "="*80 + "\n")
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/plain',
        as_attachment=True,
        download_name=f'peekaboo_complete_program_{datetime.now().strftime("%Y%m%d")}.txt'
    )

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings management"""
    if request.method == 'POST':
        settings_data = load_settings()
        
        # Update settings from form
        settings_data['training_time'] = request.form.get('training_time', '09:00')
        settings_data['timezone'] = request.form.get('timezone', 'Africa/Lagos')
        settings_data['reminder_enabled'] = request.form.get('reminder_enabled') == 'on'
        settings_data['sound_enabled'] = request.form.get('sound_enabled') == 'on'
        settings_data['theme'] = request.form.get('theme', 'light')
        
        save_settings(settings_data)
        
        return redirect(url_for('settings'))
    
    settings_data = load_settings()
    
    return render_template('settings.html', settings=settings_data)

@app.route('/reset_data', methods=['POST'])
def reset_data():
    """Reset all progress data"""
    try:
        # Create backup before reset
        backup_file = backup_database()
        
        # Clear progress data
        conn = get_db_connection()
        conn.execute("DELETE FROM progress")
        conn.execute("DELETE FROM sessions")
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "backup": backup_file})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/backup/create', methods=['POST'])
def create_backup():
    """Manually create a backup"""
    try:
        backup_file = backup_database()
        return jsonify({"success": True, "backup": backup_file})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/backup/restore/<filename>', methods=['POST'])
def restore_backup(filename):
    """Restore from a backup file"""
    try:
        backup_file = BACKUP_DIR / filename
        
        if not backup_file.exists():
            return jsonify({"success": False, "error": "Backup file not found"}), 404
        
        # Create a backup of current state before restoring
        backup_database()
        
        # Restore the backup
        shutil.copy2(backup_file, DB_PATH)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/backup/download/<filename>')
def download_backup(filename):
    """Download a backup file"""
    backup_file = BACKUP_DIR / filename
    
    if not backup_file.exists():
        return "Backup not found", 404
    
    return send_file(backup_file, as_attachment=True)

@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard statistics"""
    conn = get_db_connection()
    
    # Get total sessions completed
    total = conn.execute("SELECT COUNT(*) as count FROM progress").fetchone()['count']
    
    # Get current week progress
    current_week_data = conn.execute(
        "SELECT COUNT(*) as count FROM progress WHERE week = (SELECT MAX(week) FROM progress)"
    ).fetchone()
    current_week = current_week_data['count'] if current_week_data else 0
    
    # Get recent progress
    recent = conn.execute(
        "SELECT week, day, fluidity, endurance, power, date FROM progress ORDER BY date DESC LIMIT 5"
    ).fetchall()
    
    # Get averages
    averages = conn.execute(
        "SELECT AVG(fluidity) as fluidity, AVG(endurance) as endurance, AVG(power) as power FROM progress"
    ).fetchone()
    
    conn.close()
    
    return jsonify({
        "total_sessions": total,
        "current_week_progress": current_week,
        "recent_sessions": [dict(row) for row in recent],
        "averages": {
            "fluidity": round(averages['fluidity'] or 0, 2),
            "endurance": round(averages['endurance'] or 0, 2),
            "power": round(averages['power'] or 0, 2)
        }
    })

@app.route('/api/progress_chart')
def api_progress_chart():
    """API endpoint for progress chart data"""
    conn = get_db_connection()
    data = conn.execute(
        "SELECT week, day, fluidity, endurance, power FROM progress ORDER BY week, day"
    ).fetchall()
    conn.close()
    
    chart_data = {
        "labels": [f"W{row['week']}D{row['day']}" for row in data],
        "fluidity": [row['fluidity'] for row in data],
        "endurance": [row['endurance'] for row in data],
        "power": [row['power'] for row in data]
    }
    
    return jsonify(chart_data)

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return render_template('500.html'), 500

# Context processor to make settings available in all templates
@app.context_processor
def inject_settings():
    return dict(app_settings=load_settings())

if __name__ == '__main__':
    print("=" * 80)
    print("PEEK-A-BOO BOXING TRAINING TRACKER")
    print("=" * 80)
    print(f"Database location: {DB_PATH}")
    print(f"Settings location: {SETTINGS_PATH}")
    print(f"Backup location: {BACKUP_DIR}")
    print(f"Starting server on http://localhost:5000")
    print("=" * 80)
    
    app.run(debug=True, port=5000, host='0.0.0.0')