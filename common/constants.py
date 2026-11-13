"""Global constants for Clash of Pens."""

GAME_TITLE = "Clash of Pens"
VERSION = "0.1.0"

# Window
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors (R, G, B)
BG_COLOR = (30, 34, 45)
TEXT_COLOR = (235, 235, 235)

# Menu colors (R, G, B)
BUTTON_COLOR = (60, 70, 95)
BUTTON_HOVER_COLOR = (85, 100, 135)
BUTTON_DISABLED_COLOR = (50, 52, 60)
BUTTON_TEXT_COLOR = (235, 235, 235)
BUTTON_TEXT_DISABLED_COLOR = (120, 120, 130)

# Fonts
FONT_SIZE_TITLE = 96
FONT_SIZE_BUTTON = 40
FONT_SIZE_SMALL = 24

# Title screen
TITLE_COLOR = (255, 215, 100)
OVERLAY_COLOR = (0, 0, 0, 140)  # RGBA, semi-transparent dark layer over background
BUTTON_WIDTH = 320
BUTTON_HEIGHT = 64
BUTTON_GAP = 18

# Mode select / About screens
HEADING_COLOR = (255, 215, 100)
FONT_SIZE_HEADING = 72
MODE_BUTTON_WIDTH = 460
BACK_BUTTON_RECT = (24, SCREEN_HEIGHT - 84, 160, 56)

# Save system
SAVE_DIR_NAME = "ClashOfPens"
SAVE_FILE_NAME = "save.json"
SAVE_VERSION = 1

# Settings
SETTINGS_FILE_NAME = "settings.json"

# Board (top-down playing surface)
BOARD_RECT = (190, 110, 900, 500)  # x, y, width, height
BOARD_COLOR = (196, 164, 120)
BOARD_BORDER_COLOR = (110, 80, 50)

# Physics
PHYSICS_DAMPING = 0.0005  # fraction of velocity kept after 1 second (surface friction)
PHYSICS_SUBSTEPS = 4

# Placeholder pen (real per-pen stats come in step 3)
PEN_LENGTH = 170
PEN_WIDTH = 26
PEN_MASS = 3.0
PEN_ELASTICITY = 0.6
PEN_FRICTION = 0.4
PEN_START_HP = 100
PEN_COLOR_P1 = (70, 130, 220)
PEN_COLOR_P2 = (220, 90, 80)
PEN_OUTLINE_COLOR = (20, 20, 25)

# Shooting (drag to aim)
GRAB_MARGIN = 20  # extra pixels around a pen where a click still grabs it
MAX_PULL_DISTANCE = 160  # pixels of drag that give full power
MIN_PULL_DISTANCE = 15  # shorter drags are cancelled
MAX_SHOT_SPEED = 1200  # launch speed at full power (pixels per second)
SETTLE_SPEED = 8.0  # below this speed a pen counts as stopped
SETTLE_ANGULAR_SPEED = 0.2  # below this spin a pen counts as stopped
POWER_CURVE = 1.5  # 1.0 = linear. Higher = gentler light flicks, stronger full pulls
MAX_SPIN = 10.0  # cap on spin (radians per second) from an off-center hit

# Aiming visuals
AIM_LINE_COLOR = (255, 255, 255)
PULL_LINE_COLOR = (240, 240, 120)
TURN_RING_COLOR = (255, 255, 255)
POWER_BAR_RECT = (490, 640, 300, 22)
POWER_BAR_BG_COLOR = (50, 52, 60)

# Shrinking board
SHRINK_WARNING_TURNS = 13   # shots per player before the first warning
SHRINK_EVERY_TURNS = 2      # shots per player between later shrinks
SHRINK_STEP = 20            # pixels moved in from each side per shrink
MIN_BOARD_SIZE = (240, 140)
SHRINK_DURATION = 1.2       # seconds a shrink takes to animate
WARNING_COLOR = (230, 60, 60)
MAX_SHRINKS = 2             # board stops shrinking after this many shrinks

# Falling
WOBBLE_ZONE = 25            # pixels from the edge where a pen starts to wobble
WOBBLE_AMOUNT = 3.0         # wobble size in pixels
FALL_DURATION = 0.7         # seconds a falling pen takes to disappear
FALL_BANNER_COLOR = (255, 215, 100)

# Match rules
ROUNDS_TO_WIN = 2           # best of 3
MAX_DRAW_REPLAYS = 1        # replays allowed per match; the next draw is decided by edge distance

# Turn timer
TURN_TIME_LIMIT = 20.0      # seconds per turn
TIMER_WARNING_TIME = 5.0    # timer turns red below this
TIMER_BAR_RECT = (490, 668, 300, 10)

# ---------------------------------------------------------------------------
# Step 3: full game
# ---------------------------------------------------------------------------

# Round length and sudden death
ROUND_TURN_LIMIT = 20            # turns per player; a round with no fall is a draw after this
SUDDEN_DEATH_ENABLED = True      # False: a second draw is decided by edge distance right away
SUDDEN_DEATH_BOARD_SIZE = (480, 280)  # sudden death is played on this small centred board
SUDDEN_DEATH_TURN_LIMIT = 10     # turns per player in sudden death; still no fall = edge distance

# Pause menu
PAUSE_OVERLAY_COLOR = (0, 0, 0, 170)
PAUSE_BUTTON_WIDTH = 420

# Pen select screen
CARD_COLOR = (45, 52, 70)
CARD_HOVER_COLOR = (58, 68, 92)
CARD_SELECTED_BORDER_COLOR = (255, 215, 100)
STAT_BAR_BG_COLOR = (30, 34, 45)
STAT_BAR_FILL_COLOR = (120, 190, 255)

# AI
AI_SIM_FPS = 60                  # frames per second used when the AI tries a shot in its head
AI_SIM_MAX_FRAMES = 150          # longest a tried shot is simulated (2.5 s of game time)
AI_MIN_POWER = 0.12              # AI never flicks softer than this (fraction of full power)
AI_THINK_TIME = (0.7, 1.3)       # seconds the computer "thinks" before it flicks (min, max)
AI_PLAYER_INDEX = 1              # in Player vs Computer the computer is Player 2
