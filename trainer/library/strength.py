"""Strength movements for your kit: adjustable dumbbells, the barbell you
build from them, a flat bench, a doorway pull-up bar and the floor.

Start weights are for a beginner around 47 kg and are deliberately on the
light side -- the first set of every new exercise is a calibration set, and
the app moves the weight within that session if it was too easy.
"""
from __future__ import annotations

from . import Move, register

BREATHE_PUSH = "Breathe in on the way down, breathe out as you push."
BREATHE_PULL = "Breathe out as you pull, in as you lower."


def S(id: str, name: str, slug: str, group: str, **kw) -> Move:
    return Move(id=id, name=name, slug=slug, kind="strength", group=group, **kw)


register(
    # ------------------------------------------------------------------ chest
    S("db_bench_press", "Dumbbell Bench Press", "dumbbell-bench-press", "chest",
      muscles=("Chest", "Front shoulders", "Triceps"),
      purpose="Your main chest builder. Dumbbells let each arm work on its own "
              "and are safe without a spotter.",
      mode="db2", needs=("bench",), tracker="bench", view="side", start_kg=5.7,
      steps=(
          "Sit on the end of the bench with the dumbbells on your thighs.",
          "Lie back and use your knees to help bring the dumbbells up over your chest.",
          "Squeeze your shoulder blades together and keep your feet flat on the floor.",
          "Lower the dumbbells slowly to the sides of your chest, elbows at about 45 degrees.",
          "Press back up until your arms are straight, dumbbells over your shoulders.",
      ),
      cues=("Shoulder blades back and down", "Elbows at 45, not flared",
            "Lower for two seconds"),
      mistakes=(
          "Elbows flared straight out to the sides — hard on the shoulders.",
          "Bouncing at the bottom or cutting the range short.",
          "Lifting your hips off the bench to force the last rep.",
      ),
      easier=("db_floor_press", "incline_pushup"), similar=("db_floor_press", "pushup"),
      rep_seconds=3.5),

    S("db_floor_press", "Dumbbell Floor Press", "dumbbell-lying-on-floor-chest-press", "chest",
      muscles=("Chest", "Triceps", "Front shoulders"),
      purpose="Bench press with the floor as a built-in safety stop. Great for "
              "learning the press or if a shoulder feels cranky.",
      mode="db2", tracker="bench", view="side", start_kg=5.7,
      steps=(
          "Lie on your back with knees bent and feet flat, a dumbbell in each hand.",
          "Start with the dumbbells pressed up over your chest.",
          "Lower until your upper arms touch the floor, elbows at about 45 degrees.",
          "Pause for a moment, then press back up to straight arms.",
      ),
      cues=("Pause when your elbows touch", "Press up and slightly back", "Keep wrists straight"),
      mistakes=("Dropping your elbows onto the floor instead of touching softly.",
                "Letting the dumbbells drift toward your face."),
      harder=("db_bench_press",), rep_seconds=3.5),

    S("db_floor_fly", "Dumbbell Floor Fly", "dumbbell-floor-fly", "chest",
      muscles=("Chest", "Front shoulders"),
      purpose="Stretches and isolates the chest. The floor stops the stretch "
              "before it gets risky, which is ideal while you are new to flyes.",
      mode="db2", start_kg=4.2,
      steps=(
          "Lie on the floor, knees bent, dumbbells pressed up over your chest, palms facing each other.",
          "Keep a small fixed bend in your elbows.",
          "Open your arms in a wide arc until your upper arms touch the floor.",
          "Squeeze your chest to bring the dumbbells back together over you.",
      ),
      cues=("Hug a big tree", "Same small elbow bend all the way", "Slow on the way down"),
      mistakes=("Bending the elbows more and turning it into a press.",
                "Going too heavy — flyes are for feel, not load."),
      similar=("db_bench_press",), rep_seconds=3.5),

    S("pushup", "Push-Up", "push-up", "chest",
      muscles=("Chest", "Triceps", "Front shoulders", "Core"),
      purpose="Bodyweight chest and triceps work you can always progress: "
              "elevate your feet, add a deficit, or slow it down.",
      tracker="pushup", view="side", reps=(8, 15),
      steps=(
          "Hands slightly wider than your shoulders, fingers pointing forward.",
          "Step back into a straight line from head to heels. Squeeze your glutes.",
          "Lower your chest to about a fist from the floor, elbows at 45 degrees.",
          "Push the floor away until your arms are straight.",
      ),
      cues=("Body like a plank", "Chest to the floor, not your hips", "Elbows back, not out"),
      mistakes=("Hips sagging or piking up.", "Half reps — lower until your chest is close to the floor.",
                "Head dropping forward."),
      easier=("incline_pushup",), harder=("decline_pushup", "deficit_pushup"),
      similar=("db_floor_press",),
      rep_seconds=2.5),

    S("incline_pushup", "Incline Push-Up (hands on bench)", "incline-push-up-with-chair", "chest",
      muscles=("Chest", "Triceps", "Front shoulders"),
      purpose="An easier push-up. Raising your hands takes weight off so you "
              "can do full, clean reps.",
      needs=("bench",), tracker="pushup", view="side", reps=(8, 15),
      steps=(
          "Put your hands on the edge of the bench, slightly wider than shoulders.",
          "Walk your feet back until your body is a straight line.",
          "Lower your chest to the bench edge, then push back up.",
      ),
      cues=("Straight line, head to heels", "Chest to the bench"),
      mistakes=("Hips sagging.", "Not lowering all the way to the bench."),
      harder=("pushup",), rep_seconds=2.5),

    S("decline_pushup", "Decline Push-Up (feet on bench)", "decline-push-up", "chest",
      muscles=("Upper chest", "Front shoulders", "Triceps"),
      purpose="Feet up shifts more of your weight onto your arms and works the "
              "upper chest — the closest thing to an incline press without one.",
      needs=("bench",), tracker="pushup", view="side", reps=(6, 12),
      steps=(
          "Put your feet on the bench and your hands on the floor, slightly wider than shoulders.",
          "Brace into a straight line — do not let your hips sag.",
          "Lower your chest toward the floor, then push back up.",
      ),
      cues=("Squeeze your glutes", "Lower under control"),
      mistakes=("Hips sagging, which puts strain on the lower back.",
                "Shortening the range as you tire."),
      easier=("pushup",), harder=("deficit_pushup",), rep_seconds=2.5),

    S("deficit_pushup", "Deficit Push-Up", "deep-push-up", "chest",
      muscles=("Chest", "Front shoulders", "Triceps"),
      purpose="Hands on raised supports so your chest can sink below hand "
              "level — a bigger stretch for the chest.",
      tracker="pushup", view="side", reps=(6, 12),
      steps=(
          "Set two loaded dumbbells (or two equal stacks of thick books) on the floor, shoulder-width apart.",
          "Grip the handles, or put your hands flat on the books.",
          "Straight body from head to heels.",
          "Lower until your chest is below your hands, then press back up.",
      ),
      cues=("Sink deep, stay tight", "Control the bottom"),
      mistakes=("Supports rolling or sliding — put them against a wall.",),
      easier=("decline_pushup",), rep_seconds=3.0),

    S("diamond_pushup", "Close-Grip Push-Up", "diamond-push-up", "arms",
      muscles=("Triceps", "Chest"),
      purpose="A narrow hand position moves the work onto the triceps.",
      tracker="pushup", view="side",
      steps=(
          "Place your hands close together under your chest.",
          "Keep your elbows close to your body as you lower.",
          "Push back up to straight arms.",
      ),
      cues=("Elbows brush your ribs", "Body straight"), reps=(8, 15),
      mistakes=("Elbows flaring out.", "Hips sagging."),
      easier=("pushup",), rep_seconds=2.5),

    # ------------------------------------------------------------------- back
    S("db_bent_row", "Bent-Over Dumbbell Row", "dumbbell-bent-over-row", "back",
      muscles=("Upper back", "Lats", "Rear shoulders", "Biceps"),
      purpose="Builds the upper back and lats that balance out all the pressing.",
      mode="db2", tracker="row", view="side", start_kg=5.7,
      steps=(
          "Stand with feet hip-width, a dumbbell in each hand.",
          "Push your hips back and bend forward until your torso is about 45 degrees, back flat.",
          "Let the dumbbells hang straight down from your shoulders.",
          "Pull them toward your lower ribs, squeezing your shoulder blades together.",
          "Lower slowly until your arms are straight again.",
      ),
      cues=("Flat back, hinge at the hips", "Elbows to your back pockets", "Squeeze, then lower slowly"),
      mistakes=("Standing up more with each rep.", "Rounding your back.",
                "Jerking the weight up with your hips."),
      easier=("one_arm_row",), similar=("one_arm_row", "bb_row"), rep_seconds=3.0),

    S("one_arm_row", "One-Arm Dumbbell Row (bench-supported)", "dumbbell-single-arm-bent-over-row", "back",
      muscles=("Lats", "Upper back", "Biceps"),
      purpose="Supporting yourself on the bench protects your lower back and "
              "lets you pull more weight with each side.",
      mode="db1", needs=("bench",), tracker="row", view="side", per_side=True, start_kg=7.2,
      steps=(
          "Put one knee and the same-side hand on the bench, other foot on the floor.",
          "Hold the dumbbell in your free hand, arm hanging straight down.",
          "Pull the dumbbell up toward your hip, elbow close to your body.",
          "Lower all the way down with control. Finish all reps, then switch sides.",
      ),
      cues=("Pull to your hip, not your chest", "Do not twist your torso", "Full stretch at the bottom"),
      mistakes=("Rotating your chest open to heave the weight up.", "Cutting the stretch at the bottom short."),
      similar=("db_bent_row",), rep_seconds=2.5),

    S("bb_row", "Barbell Bent-Over Row", "barbell-bent-over-row", "back",
      muscles=("Upper back", "Lats", "Rear shoulders"),
      purpose="Row with both arms on one bar — lets you load heavier than the pair of dumbbells.",
      mode="bb", tracker="row", view="side", start_kg=9.9,
      steps=(
          "Hold the bar with hands just wider than your knees, palms facing you.",
          "Hinge forward to about 45 degrees with a flat back and soft knees.",
          "Pull the bar to your belly button, squeezing your shoulder blades.",
          "Lower until your arms are straight.",
      ),
      cues=("Bar to your belly button", "Stay bent over"),
      mistakes=("Standing up as you pull.", "Rounding your lower back."),
      similar=("db_bent_row",), rep_seconds=3.0),

    S("pullup_negative", "Pull-Up Negative", "pull-up-negative", "back",
      muscles=("Lats", "Biceps", "Upper back", "Grip"),
      purpose="The fastest route to your first pull-up. Jump or step to the top "
              "and lower yourself as slowly as you can — you are stronger "
              "lowering than lifting.",
      needs=("pullup_bar",), tracker="pullup", view="front", rep_seconds=8.0, reps=(3, 5),
      steps=(
          "Stand on a chair or jump so your chin is above the bar, palms facing away.",
          "Hold the top position for a second, chest up and shoulders down.",
          "Lower yourself as slowly as you can — aim for 5 seconds — until your arms are straight.",
          "Put your feet down, reset, and repeat.",
      ),
      cues=("Count five on the way down", "Shoulders away from your ears", "Fully straight at the bottom"),
      mistakes=("Dropping quickly through the bottom half.", "Swinging your legs."),
      # The pullover is the no-bar stand-in: it works the lats through a
      # similar overhead arc.
      easier=("dead_hang",), harder=("chinup",), similar=("db_pullover",)),

    S("chinup", "Chin-Up", "chin-up", "back",
      muscles=("Lats", "Biceps", "Upper back"),
      purpose="Palms-facing-you grip brings the biceps in — usually the first "
              "full rep people get.",
      needs=("pullup_bar",), tracker="pullup", view="front", rep_seconds=4.0, reps=(3, 8),
      steps=(
          "Grip the bar shoulder-width with palms facing you.",
          "Hang with straight arms, then pull your chest toward the bar.",
          "Get your chin over the bar, then lower slowly to straight arms.",
          "If you cannot finish a rep, finish the set with slow negatives.",
      ),
      cues=("Chest to the bar", "Lower slowly"),
      mistakes=("Kicking your legs to get up.", "Half reps from bent arms."),
      easier=("pullup_negative",), harder=("pullup",)),

    S("pullup", "Pull-Up", "pull-up", "back",
      muscles=("Lats", "Upper back", "Biceps"),
      purpose="The king of upper-body pulling exercises.",
      needs=("pullup_bar",), tracker="pullup", view="front", rep_seconds=4.0, reps=(3, 8),
      steps=(
          "Grip the bar slightly wider than shoulders, palms facing away.",
          "From a dead hang, pull your elbows down toward your hips.",
          "Chin over the bar, then lower under control to straight arms.",
      ),
      cues=("Elbows to your hips", "Full hang every rep"),
      mistakes=("Kipping or swinging.", "Not reaching straight arms at the bottom."),
      easier=("chinup",)),

    S("dead_hang", "Dead Hang", "dead-hang-stretch", "back",
      muscles=("Grip", "Lats", "Shoulders"),
      purpose="Builds the grip and shoulder strength you need for pull-ups.",
      needs=("pullup_bar",), hold=True, seconds=30,
      steps=(
          "Grab the bar with straight arms, palms facing away.",
          "Let your body hang, then pull your shoulders slightly down away from your ears.",
          "Breathe slowly and hold.",
      ),
      cues=("Shoulders down", "Breathe"),
      mistakes=("Shrugging your shoulders up to your ears.",),
      harder=("pullup_negative",)),

    S("db_pullover", "Dumbbell Pullover", "dumbbell-pullover", "back",
      muscles=("Lats", "Chest", "Triceps (long head)"),
      purpose="Stretches and works the lats and chest together.",
      mode="db1", needs=("bench",), start_kg=5.7,
      steps=(
          "Lie across or along the bench, holding one dumbbell with both hands over your chest.",
          "Keep a slight bend in your elbows and lower the dumbbell back behind your head.",
          "Go until you feel a stretch in your lats, then pull it back over your chest.",
      ),
      cues=("Arms stay slightly bent", "Ribs down"),
      mistakes=("Bending the elbows a lot and turning it into a triceps exercise.",
                "Arching your lower back off the bench."),
      rep_seconds=3.5),

    S("rear_delt_fly", "Bent-Over Rear Delt Fly", "dumbbell-rear-fly", "shoulders",
      muscles=("Rear shoulders", "Upper back"),
      purpose="Rear shoulders get missed by pressing. This keeps your shoulders "
              "balanced and your posture good.",
      mode="db2", start_kg=1.7,
      steps=(
          "Hinge forward until your chest is nearly parallel to the floor, dumbbells hanging.",
          "With a soft bend in your elbows, raise your arms out to the sides.",
          "Stop at shoulder height, squeeze, then lower slowly.",
      ),
      cues=("Lead with your little fingers", "Light weight, slow reps"),
      mistakes=("Swinging the weights up with your body.", "Shrugging your shoulders."),
      rep_seconds=3.0),

    # -------------------------------------------------------------- shoulders
    S("bb_ohp", "Standing Barbell Overhead Press", "barbell-standing-military-press-without-rack", "shoulders",
      muscles=("Shoulders", "Triceps", "Upper chest", "Core"),
      purpose="The best all-round shoulder builder, and your barbell runs out "
              "slowest on this lift.",
      mode="bb", tracker="press", view="front", start_kg=8.9,
      steps=(
          "Clean the bar to your shoulders: hands just outside shoulder-width, elbows slightly in front of the bar.",
          "Feet hip-width, squeeze your glutes and brace your stomach.",
          "Press the bar straight up, moving your head back slightly to let it pass.",
          "Lock out overhead with the bar over the middle of your feet, then lower to your collarbone.",
      ),
      cues=("Squeeze your glutes, do not lean back", "Head through at the top", "Bar to your collarbone"),
      mistakes=("Leaning back so far it becomes a standing incline press.", "Pressing the bar forward around your face."),
      easier=("db_seated_press",), similar=("db_seated_press", "arnold_press"), rep_seconds=3.0),

    S("db_seated_press", "Seated Dumbbell Shoulder Press", "dumbbell-seated-shoulder-press", "shoulders",
      muscles=("Shoulders", "Triceps"),
      purpose="Sitting removes the balance challenge so your shoulders do all the work.",
      mode="db2", needs=("bench",), tracker="press", view="front", start_kg=4.7,
      steps=(
          "Sit upright on the end of the bench, feet flat, dumbbells at shoulder height.",
          "Palms facing forward, elbows slightly in front of your body.",
          "Press up until your arms are straight, dumbbells nearly touching.",
          "Lower back down to ear level.",
      ),
      cues=("Sit tall, ribs down", "Lower to your ears"),
      mistakes=("Arching your lower back hard.", "Stopping the lowering halfway."),
      similar=("bb_ohp", "arnold_press"), rep_seconds=3.0),

    S("arnold_press", "Arnold Press", "dumbbell-arnold-press", "shoulders",
      muscles=("Front and side shoulders", "Triceps"),
      purpose="A press with a twist that works more of the shoulder through a longer path.",
      mode="db2", tracker="press", view="front", start_kg=4.2,
      steps=(
          "Start with the dumbbells in front of your shoulders, palms facing you.",
          "As you press up, rotate your palms to face forward.",
          "Reverse the rotation on the way down.",
      ),
      cues=("Rotate as you rise", "Smooth, not jerky"),
      mistakes=("Rushing the rotation.",),
      similar=("db_seated_press",), rep_seconds=3.5),

    S("lateral_raise", "Dumbbell Lateral Raise", "dumbbell-lateral-raise", "shoulders",
      muscles=("Side shoulders",),
      purpose="Side shoulders give you width. They are small muscles, so light "
              "weight and higher reps work best.",
      mode="db2", tracker="lateral", view="front", start_kg=1.7, increment=0.10,
      steps=(
          "Stand tall, dumbbells at your sides, slight bend in your elbows.",
          "Raise your arms out to the sides until they are level with your shoulders.",
          "Pause for a moment, then lower slowly.",
      ),
      cues=("Lead with your elbows", "Stop at shoulder height", "No swinging"),
      mistakes=("Using your legs and back to swing the weights.", "Shrugging toward your ears.",
                "Going above shoulder height."),
      rep_seconds=2.5),

    S("pike_pushup", "Pike Push-Up", "pike-push-up", "shoulders",
      muscles=("Shoulders", "Triceps"),
      purpose="A bodyweight overhead press.",
      tracker="pike", view="side", reps=(6, 12),
      steps=(
          "Start in a push-up position, then walk your feet in and lift your hips high into an upside-down V.",
          "Bend your elbows to lower the top of your head toward the floor in front of your hands.",
          "Push back up to straight arms.",
      ),
      cues=("Hips high", "Head forms a triangle with your hands"),
      mistakes=("Letting your hips drop into a normal push-up.",),
      harder=("elevated_pike",), similar=("db_seated_press",), rep_seconds=3.0),

    # ------------------------------------------------------------------- arms
    S("db_curl", "Dumbbell Biceps Curl", "dumbbell-standing-biceps-curl", "arms",
      muscles=("Biceps", "Forearms"),
      purpose="Direct biceps work — rows build them too, but curls finish the job.",
      mode="db2", tracker="curl", view="side", start_kg=4.2, increment=0.05,
      steps=(
          "Stand tall, dumbbells at your sides, palms facing forward.",
          "Keep your elbows pinned to your sides and curl the weights up to your shoulders.",
          "Squeeze, then lower slowly all the way until your arms are straight.",
      ),
      cues=("Elbows glued to your sides", "All the way down", "No body swing"),
      mistakes=("Swinging your back to lift the weight.", "Elbows drifting forward.",
                "Stopping short of straight arms."),
      similar=("hammer_curl", "bb_curl"), rep_seconds=3.0),

    S("hammer_curl", "Hammer Curl", "dumbbell-hammer-curl", "arms",
      muscles=("Brachialis", "Biceps", "Forearms"),
      purpose="A neutral grip hits the muscle under the biceps and your forearms — "
              "this builds arm thickness.",
      mode="db2", tracker="curl", view="side", start_kg=4.7, increment=0.05,
      steps=(
          "Hold the dumbbells at your sides with palms facing each other.",
          "Curl them up keeping your palms facing in, like holding a hammer.",
          "Lower slowly to straight arms.",
      ),
      cues=("Thumbs up the whole way", "Elbows stay still"),
      mistakes=("Swinging.", "Elbows drifting forward."),
      similar=("db_curl",), rep_seconds=3.0),

    S("bb_curl", "Barbell Curl", "barbell-curl", "arms",
      muscles=("Biceps", "Forearms"),
      purpose="Both arms on one bar lets you load more than a dumbbell pair.",
      mode="bb", tracker="curl", view="side", start_kg=7.4, increment=0.05,
      steps=(
          "Hold the bar shoulder-width, palms facing forward, arms straight.",
          "Curl the bar up to your shoulders keeping your elbows at your sides.",
          "Lower slowly to straight arms.",
      ),
      cues=("Elbows still", "Squeeze at the top"),
      mistakes=("Leaning back to heave the bar.",),
      similar=("db_curl",), rep_seconds=3.0),

    S("oh_triceps_ext", "Overhead Triceps Extension", "dumbbell-standing-triceps-extension", "arms",
      muscles=("Triceps (long head)",),
      purpose="Overhead puts the biggest part of the triceps on stretch — the "
              "triceps make up most of your upper arm.",
      # Not camera-tracked: overhead, the forearms and dumbbell sit behind the
      # head and the pose model cannot read the elbow (checked on the demo).
      mode="db1", start_kg=5.7, increment=0.05,
      steps=(
          "Hold ONE dumbbell with both hands under the top plates (the video uses two; either works).",
          "Press it overhead with straight arms, elbows pointing forward.",
          "Bend your elbows to lower the dumbbell behind your head.",
          "Straighten your arms to press it back up. Keep your upper arms still.",
      ),
      cues=("Elbows point forward", "Deep stretch behind your head", "Ribs down"),
      mistakes=("Elbows flaring wide.", "Arching your lower back."),
      similar=("skull_crusher",), rep_seconds=3.0),

    S("skull_crusher", "Dumbbell Skull Crusher", "dumbbell-lying-triceps-extension", "arms",
      muscles=("Triceps",),
      purpose="Lying triceps extension — isolates the triceps with your back supported.",
      mode="db2", needs=("bench",), tracker="triceps", view="side", start_kg=4.2, increment=0.05,
      steps=(
          "Lie on the bench with the dumbbells pressed up over your chest, palms facing each other.",
          "Keeping your upper arms still, bend your elbows to lower the dumbbells beside your head.",
          "Straighten your arms to lift them back up.",
      ),
      cues=("Upper arms stay still", "Control the bottom"),
      mistakes=("Letting the elbows swing back and forth.",),
      similar=("oh_triceps_ext",), rep_seconds=3.0),

    S("bench_dip", "Bench Dip", "triceps-dip-bench-leg", "arms",
      muscles=("Triceps", "Front shoulders"),
      purpose="Bodyweight triceps work using the bench — or any sturdy chair.",
      needs=("bench",), tracker="triceps", view="side", reps=(8, 15),
      steps=(
          "Sit on the edge of the bench (or a chair pushed against a wall), hands beside your hips, fingers forward.",
          "Slide your hips off the bench, knees bent, feet flat.",
          "Bend your elbows to lower your hips until your upper arms are about parallel to the floor.",
          "Press back up to straight arms.",
      ),
      cues=("Stay close to the bench", "Elbows point back"),
      mistakes=("Sinking too deep — stop at upper arms parallel to protect your shoulders.",
                "Elbows flaring out."),
      similar=("diamond_pushup",), rep_seconds=2.5),

    # ------------------------------------------------------------------- legs
    S("goblet_squat", "Goblet Squat", "dumbbell-goblet-squat", "legs",
      muscles=("Quads", "Glutes", "Adductors", "Core"),
      purpose="Your main squat. Holding the weight in front keeps you upright "
              "and teaches good depth.",
      mode="db1", tracker="squat", view="side", start_kg=7.2, increment=0.05,
      steps=(
          "Hold one dumbbell vertically against your chest, both hands under the top plates.",
          "Feet a bit wider than shoulders, toes turned out slightly.",
          "Sit down between your heels, keeping your chest up and your knees going over your toes.",
          "Go until your thighs are at least parallel to the floor.",
          "Drive through your whole foot to stand up tall.",
      ),
      cues=("Chest up", "Knees out over your toes", "Sit between your heels"),
      mistakes=("Knees caving inward.", "Heels lifting off the floor.", "Stopping above parallel."),
      easier=("box_squat",), similar=("sumo_squat",), rep_seconds=3.5),

    S("bw_squat", "Bodyweight Squat", "squat", "legs",
      muscles=("Quads", "Glutes"),
      purpose="Learn the squat pattern without load. Without dumbbells, go "
              "slow: three seconds down, a pause at the bottom.",
      tracker="squat", view="side", reps=(15, 25),
      steps=(
          "Feet shoulder-width, arms forward for balance.",
          "Sit down and back until your thighs are parallel to the floor.",
          "Stand back up, squeezing your glutes at the top.",
      ),
      cues=("Chest up", "Knees out"),
      mistakes=("Knees caving in.", "Heels lifting."),
      harder=("goblet_squat", "pistol_box"), similar=("wall_sit",), rep_seconds=2.5),

    S("box_squat", "Box Squat to Bench", "bodyweight-bench-squat", "legs",
      muscles=("Quads", "Glutes"),
      purpose="The bench behind you sets the depth and gives you confidence.",
      needs=("bench",), tracker="squat", view="side", reps=(12, 20),
      steps=(
          "Stand in front of the bench, feet shoulder-width.",
          "Sit back until you lightly touch the bench — do not flop down.",
          "Stand back up without rocking.",
      ),
      cues=("Touch and go", "Chest up"),
      mistakes=("Dropping onto the bench and rocking up.",),
      harder=("goblet_squat", "pistol_box"), rep_seconds=3.0),

    S("sumo_squat", "Dumbbell Sumo Squat", "dumbbell-goblet-sumo-squat", "legs",
      muscles=("Inner thighs", "Glutes", "Quads"),
      purpose="Wide stance moves more work onto the glutes and inner thighs.",
      mode="db1", tracker="squat", view="side", start_kg=8.2, increment=0.05,
      steps=(
          "Stand with a wide stance, toes turned out about 30 degrees.",
          "Hold one dumbbell hanging between your legs or at your chest.",
          "Squat straight down, knees tracking over your toes.",
          "Stand up and squeeze your glutes.",
      ),
      cues=("Knees out over your toes", "Straight down, straight up"),
      mistakes=("Knees collapsing inward.",),
      similar=("goblet_squat",), rep_seconds=3.0),

    S("bss", "Bulgarian Split Squat", "dumbbell-bulgarian-split-squat-with-support", "legs",
      muscles=("Quads", "Glutes", "Adductors"),
      purpose="Your best long-term leg builder. One leg carries what both hands "
              "hold, so your plates stay challenging for a long time.",
      mode="db2", needs=("bench",), tracker="lunge", view="side", per_side=True,
      start_kg=4.2, increment=0.05, rep_seconds=3.5,
      steps=(
          "Stand about two steps in front of the bench, facing away from it.",
          "Put the top of one foot on the bench behind you.",
          "Lower straight down until your front thigh is about parallel to the floor.",
          "Drive through your front heel to stand back up. Finish all reps, then switch legs.",
      ),
      cues=("Straight down, like an elevator", "Front heel stays down", "Slight forward lean is fine"),
      mistakes=("Front foot too close to the bench, so your heel lifts.",
                "Pushing off the back leg instead of the front.",
                "Front knee caving inward."),
      easier=("split_squat",), similar=("reverse_lunge",)),

    S("split_squat", "Dumbbell Split Squat", "dumbbell-split-squat", "legs",
      muscles=("Quads", "Glutes"),
      purpose="The Bulgarian split squat with your back foot on the floor — "
              "easier to balance.",
      mode="db2", tracker="lunge", view="side", per_side=True, start_kg=4.2,
      increment=0.05, rep_seconds=3.0,
      steps=(
          "Take a long stride, one foot forward and one back, holding the dumbbells at your sides.",
          "Lower your back knee toward the floor, keeping your torso upright.",
          "Push through your front foot to come back up. Finish all reps, then switch legs.",
      ),
      cues=("Back knee to the floor", "Torso tall"),
      mistakes=("Stance too short.", "Front knee caving in."),
      harder=("bss",), similar=("reverse_lunge",)),

    S("reverse_lunge", "Dumbbell Reverse Lunge", "dumbbell-rear-lunge", "legs",
      muscles=("Quads", "Glutes", "Hamstrings"),
      purpose="Stepping back is easier on the knees than a forward lunge and "
              "trains balance.",
      mode="db2", tracker="lunge", view="side", per_side=True, start_kg=4.2,
      increment=0.05, rep_seconds=3.5,
      steps=(
          "Stand tall with a dumbbell in each hand.",
          "Step one foot back and lower until both knees are bent at about 90 degrees.",
          "Push through your front foot to step back to standing. Finish all reps on that leg, then switch.",
      ),
      cues=("Long step back", "Drive through the front heel"),
      mistakes=("Short step, so the front knee shoots forward.", "Wobbling — slow down."),
      easier=("split_squat",), similar=("bss",)),

    S("step_up", "Dumbbell Step-Up", "dumbbell-step-up", "legs",
      muscles=("Quads", "Glutes"),
      purpose="A single-leg move that strengthens the knee for everyday life.",
      mode="db2", needs=("bench",), per_side=True, start_kg=1.7, increment=0.05,
      rep_seconds=3.5,
      steps=(
          "Stand facing the bench with a dumbbell in each hand.",
          "Put one whole foot on the bench.",
          "Push through that foot to stand up on the bench — do not push off the back foot.",
          "Step down slowly with the other foot. Finish all reps, then switch legs.",
      ),
      cues=("Work from the top leg only", "Step down slowly"),
      mistakes=("Bouncing off the bottom foot.", "Bench too high — the bench should be about knee height."),
      similar=("reverse_lunge",)),

    S("calf_raise", "Single-Leg Calf Raise", "dumbbell-standing-single-leg-calf-raise", "legs",
      muscles=("Calves",),
      purpose="Calves respond to full stretch and lots of reps.",
      mode="db1", per_side=True, start_kg=1.7, increment=0.10, rep_seconds=2.5,
      steps=(
          "Stand on one foot on the edge of a step or plate stack, holding a dumbbell on the same side.",
          "Hold something with your free hand for balance.",
          "Lower your heel as far as it goes, pause, then rise as high as you can.",
          "Finish all reps, then switch sides.",
      ),
      cues=("Full stretch at the bottom", "Pause at the top"),
      mistakes=("Bouncing through short reps.",)),

    # ------------------------------------------------------ glutes & hamstrings
    S("bb_rdl", "Barbell Romanian Deadlift", "barbell-romanian-deadlift", "glutes",
      muscles=("Hamstrings", "Glutes", "Lower back"),
      purpose="The best hamstring and glute builder you can load. Teaches the "
              "hip hinge you use every time you pick something up.",
      mode="bb", tracker="hinge", view="side", start_kg=13.9, increment=0.05,
      steps=(
          "Stand tall holding the bar at your thighs, hands just outside your legs.",
          "Soften your knees slightly and keep them there.",
          "Push your hips back and let the bar slide down your thighs, back flat.",
          "Stop when you feel a strong hamstring stretch — usually just below the knees.",
          "Drive your hips forward to stand tall and squeeze your glutes.",
      ),
      cues=("Hips back, not down", "Bar stays against your legs", "Flat back"),
      mistakes=("Bending the knees and turning it into a squat.", "Rounding your back to go lower.",
                "Bar drifting away from your legs."),
      easier=("db_rdl",), similar=("db_rdl",), rep_seconds=3.5),

    S("db_rdl", "Dumbbell Romanian Deadlift", "dumbbell-romanian-deadlift", "glutes",
      muscles=("Hamstrings", "Glutes"),
      purpose="Same hinge as the barbell version, with dumbbells.",
      mode="db2", tracker="hinge", view="side", start_kg=7.2, increment=0.05,
      steps=(
          "Stand tall with a dumbbell in front of each thigh.",
          "Soft knees, push your hips back, slide the dumbbells down your legs.",
          "Feel the hamstring stretch, then drive your hips forward to stand.",
      ),
      cues=("Hips back", "Dumbbells close to your legs"),
      mistakes=("Squatting it down.", "Rounding your back."),
      harder=("bb_rdl",), similar=("bb_rdl",), rep_seconds=3.5),

    S("sl_rdl", "Single-Leg Romanian Deadlift", "dumbbell-single-leg-deadlift", "glutes",
      muscles=("Hamstrings", "Glutes", "Balance"),
      purpose="Works each hamstring on its own and builds balance. With your "
              "plates, this stays challenging for a year.",
      mode="db2", tracker="hinge", view="side", per_side=True, start_kg=1.7,
      increment=0.05, rep_seconds=4.0,
      steps=(
          "Stand on one leg with a slight knee bend, dumbbells in front of your thighs.",
          "Hinge forward as the other leg extends straight back, like a see-saw.",
          "Keep your hips square to the floor — do not let the back hip open up.",
          "Go until your torso is nearly parallel, then return to standing. Switch legs after the set.",
      ),
      cues=("See-saw: chest down, heel back", "Hips square", "Slow and balanced"),
      mistakes=("Rotating the hips open.", "Rushing and losing balance — touch a wall if needed."),
      easier=("db_rdl",)),

    S("db_hip_thrust", "Dumbbell Hip Thrust", "dumbbell-hip-thrust", "glutes",
      muscles=("Glutes", "Hamstrings"),
      purpose="Loads the glutes hardest at full hip extension, where squats are easiest.",
      mode="db1", needs=("bench",), tracker="bridge", view="side", start_kg=10.2,
      increment=0.05, rep_seconds=3.0,
      steps=(
          "Sit on the floor with your upper back against the side of the bench.",
          "Place a dumbbell across your hips, held with both hands. A folded towel helps.",
          "Feet flat, about hip-width, knees bent.",
          "Drive through your heels to lift your hips until your body is flat from shoulders to knees.",
          "Squeeze your glutes for a second, then lower.",
      ),
      cues=("Chin tucked, ribs down", "Squeeze at the top", "Shins vertical at the top"),
      mistakes=("Arching your lower back instead of extending your hips.",
                "Feet too far away, which shifts the work to your hamstrings."),
      easier=("glute_bridge",), similar=("bb_hip_thrust",)),

    S("bb_hip_thrust", "Barbell Hip Thrust", "barbell-hip-thrust", "glutes",
      muscles=("Glutes", "Hamstrings"),
      purpose="Hip thrust with the barbell when one dumbbell is no longer enough.",
      mode="bb", needs=("bench",), tracker="bridge", view="side", start_kg=13.9,
      increment=0.05, rep_seconds=3.0,
      steps=(
          "Upper back against the bench, barbell rolled over your hips with a towel for padding.",
          "Drive through your heels to lift your hips until your body is flat.",
          "Squeeze, then lower under control.",
      ),
      cues=("Ribs down", "Squeeze at the top"),
      mistakes=("Over-arching the lower back.",),
      similar=("db_hip_thrust",)),

    S("glute_bridge", "Glute Bridge", "glute-bridge-two-legs-on-floor", "glutes",
      muscles=("Glutes", "Hamstrings"),
      purpose="Simple floor bridge — great for warming up the glutes.",
      tracker="bridge", view="side", reps=(12, 20),
      steps=(
          "Lie on your back, knees bent, feet flat and close to your hips.",
          "Press through your heels to lift your hips until your body is straight from shoulders to knees.",
          "Squeeze your glutes, then lower slowly.",
      ),
      cues=("Squeeze at the top", "Heels down"),
      mistakes=("Pushing through your toes.", "Arching your back."),
      harder=("db_hip_thrust", "sl_glute_bridge"), rep_seconds=2.5),

    S("sl_glute_bridge", "Single-Leg Glute Bridge", "glute-bridge-one-leg-on-floor-bent-knee", "glutes",
      muscles=("Glutes", "Hamstrings"),
      purpose="A one-leg bridge — much harder than it looks.",
      tracker="bridge", view="side", per_side=True, reps=(10, 15),
      steps=(
          "Lie on your back, one foot flat, the other knee pulled toward your chest.",
          "Drive through the planted heel to lift your hips level.",
          "Lower slowly. Finish all reps, then switch sides.",
      ),
      cues=("Hips level", "Drive through the heel"),
      mistakes=("Hips tilting to one side.",),
      easier=("glute_bridge",), harder=("sl_hip_thrust",), rep_seconds=2.5),

    S("sl_hip_thrust", "Single-Leg Hip Thrust", "dumbbell-single-leg-hip-thrust", "glutes",
      muscles=("Glutes", "Hamstrings"),
      purpose="A hip thrust on one leg — doubles the load on each glute without more plates.",
      mode="bw", needs=("bench",), tracker="bridge", view="side", per_side=True,
      rep_seconds=3.0, reps=(10, 15),
      steps=(
          "Upper back against the bench, one foot planted, the other leg lifted.",
          "Drive through the planted heel to lift your hips level with your shoulders.",
          "Squeeze, lower slowly. Finish all reps, then switch legs.",
          "Once 15 easy reps per leg, hold a dumbbell on your hips.",
      ),
      cues=("Hips level", "Squeeze at the top"),
      mistakes=("Hips rotating to one side.",),
      easier=("sl_glute_bridge",), similar=("db_hip_thrust",)),

    # ------------------------------------------------------------------- core
    S("plank", "Front Plank", "front-plank", "core",
      muscles=("Abs", "Deep core", "Shoulders"),
      purpose="Teaches you to brace your trunk — the skill that protects your "
              "back on every lift.",
      hold=True, seconds=30, view="side", reps=(30, 60),
      steps=(
          "Forearms on the floor, elbows under your shoulders.",
          "Step your feet back into a straight line from head to heels.",
          "Squeeze your glutes, pull your belly button in, and breathe steadily.",
      ),
      cues=("Squeeze your glutes", "Do not hold your breath"),
      mistakes=("Hips sagging toward the floor.", "Hips piked up high."),
      harder=("weighted_plank",), similar=("hollow_hold",)),

    S("weighted_plank", "Weighted Plank", "weighted-front-plank", "core",
      muscles=("Abs", "Deep core"),
      purpose="Plank with a plate on your back once 60 seconds is easy.",
      hold=True, seconds=40, view="side", needs=("dumbbells",),
      steps=(
          "Get into a forearm plank.",
          "Have a plate placed on your upper back, or slide it on carefully.",
          "Hold a straight line and breathe.",
      ),
      cues=("Straight line", "Breathe"),
      mistakes=("Sagging under the weight.",),
      easier=("plank",)),

    S("side_plank", "Side Plank", "side-plank-version-2", "core",
      muscles=("Obliques", "Deep core", "Glute med"),
      purpose="Builds the side of your core, which keeps your spine stable "
              "during single-leg work.",
      hold=True, per_side=True, seconds=25, view="front", reps=(20, 40),
      steps=(
          "Lie on your side, forearm under your shoulder, legs straight and stacked.",
          "Lift your hips so your body is a straight line.",
          "Hold, then switch sides.",
      ),
      cues=("Hips high", "Straight line"),
      mistakes=("Hips dropping.", "Rolling forward."),
      easier=("side_plank_knee",)),

    S("side_plank_knee", "Side Plank (from knees)", "side-plank-beginner", "core",
      muscles=("Obliques", "Deep core"),
      purpose="An easier side plank, supported on your bottom knee.",
      hold=True, per_side=True, seconds=25, view="front", reps=(20, 40),
      steps=(
          "Lie on your side with knees bent, forearm under your shoulder.",
          "Lift your hips so your body is straight from head to knees.",
          "Hold, then switch sides.",
      ),
      cues=("Hips forward and high",),
      mistakes=("Hips sagging back.",),
      harder=("side_plank",)),

    S("dead_bug", "Dead Bug", "dead-bug", "core",
      muscles=("Deep core", "Abs"),
      purpose="Trains your core to stay still while your arms and legs move — "
              "exactly what it has to do when you lift.",
      per_side=False, rep_seconds=4.0, reps=(8, 12),
      steps=(
          "Lie on your back, arms pointing at the ceiling, knees bent at 90 degrees over your hips.",
          "Press your lower back gently into the floor.",
          "Slowly extend one arm overhead and the opposite leg out straight, hovering above the floor.",
          "Return and switch sides. Each side counts as one rep.",
      ),
      cues=("Lower back stays down", "Slow and controlled", "Breathe out as you extend"),
      mistakes=("Lower back arching off the floor.", "Moving too fast."),
      similar=("bird_dog",)),

    S("hanging_knee_raise", "Hanging Knee Raise", "hanging-leg-tuck", "core",
      muscles=("Lower abs", "Hip flexors", "Grip"),
      purpose="Hanging core work that also builds the grip you need for pull-ups.",
      needs=("pullup_bar",), tracker="knee_raise", view="side", rep_seconds=3.0, reps=(8, 12),
      steps=(
          "Hang from the bar with straight arms.",
          "Without swinging, bring your knees up toward your chest, curling your pelvis up.",
          "Lower your legs slowly until straight.",
      ),
      cues=("No swinging", "Curl your hips up", "Lower slowly"),
      mistakes=("Swinging to get the legs up.", "Only lifting the knees without curling the pelvis."),
      easier=("lying_leg_raise",)),

    S("lying_leg_raise", "Lying Leg Raise", "lying-leg-raise", "core",
      muscles=("Lower abs", "Hip flexors"),
      purpose="An easier version of the hanging leg raise.",
      rep_seconds=3.0, reps=(8, 15),
      steps=(
          "Lie on your back, hands under your hips, legs straight.",
          "Keep your lower back down and lift your legs until they point at the ceiling.",
          "Lower slowly, stopping just before your heels touch the floor.",
      ),
      cues=("Lower back stays down", "Slow on the way down"),
      mistakes=("Back arching as the legs lower.",),
      harder=("hanging_knee_raise",)),

    S("hollow_hold", "Hollow Body Hold", "hollow-hold", "core",
      muscles=("Abs", "Deep core"),
      purpose="A demanding full-core hold from gymnastics.",
      hold=True, seconds=20,
      steps=(
          "Lie on your back, press your lower back into the floor.",
          "Lift your shoulders and legs off the floor, arms reaching past your ears.",
          "Bend your knees to make it easier. Hold.",
      ),
      cues=("Lower back glued down",),
      mistakes=("Lower back lifting off the floor.",),
      similar=("plank",)),

    S("russian_twist", "Russian Twist", "russian-twist", "core",
      muscles=("Obliques", "Abs"),
      purpose="Rotation for your obliques.",
      rep_seconds=2.0,
      steps=(
          "Sit with knees bent and heels on the floor, lean back slightly with a straight back.",
          "Hold your hands together (or a light dumbbell) and rotate your torso side to side.",
          "Each side counts as one rep.",
      ),
      cues=("Rotate your ribs, not just your arms",),
      mistakes=("Rounding your back.",)),
)
