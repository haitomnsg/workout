"""Moves for days away from your dumbbells.

Everything here needs at most a sturdy chair ("bench"), a table you can lie
under ("table"), a door, a wall and a towel. Without weights the ways to make
a move harder are leverage, one leg instead of two, range of motion and slow
lowering -- so the lists of easier/harder variations matter more here than
in the dumbbell program, and each move carries its own rep range.

Rep counters are only attached where the movement is the same one a tracker
was verified on (a split squat is a split squat with or without dumbbells).
"""
from __future__ import annotations

from . import Move, register


def S(id: str, name: str, slug: str, group: str, **kw) -> Move:
    return Move(id=id, name=name, slug=slug, kind="strength", group=group, **kw)


register(
    # ------------------------------------------------------------------ back
    S("table_row_bent", "Table Row (knees bent)", "inverted-row-bent-knees", "back",
      muscles=("Upper back", "Lats", "Biceps", "Rear shoulders"),
      purpose="Your main back builder without dumbbells. Lying under a table "
              "and pulling your chest up to it is a row with your own body "
              "as the weight.",
      needs=("table",), reps=(8, 15), rep_seconds=3.0,
      steps=(
          "Check the table first: solid, not on wheels, and it does not tip when you pull on its edge.",
          "Lie on your back under the table with your chest below its edge.",
          "Grip the edge with both hands, shoulder-width apart. Bend your knees, feet flat.",
          "Lift your hips so your body is straight from shoulders to knees.",
          "Pull your chest up to the edge, squeezing your shoulder blades together, then lower to straight arms.",
      ),
      cues=("Chest to the table", "Hips stay up", "Squeeze, then lower slowly"),
      mistakes=("Hips sagging so only your arms move.", "Shrugging your shoulders toward your ears.",
                "Using a light or wobbly table — it must not move."),
      harder=("table_row",), similar=("door_row",)),

    S("table_row", "Table Row (legs straight)", "inverted-row", "back",
      muscles=("Upper back", "Lats", "Biceps", "Rear shoulders"),
      purpose="Straight legs put more of your bodyweight on your arms — the "
              "next step once the bent-knee row is easy.",
      needs=("table",), reps=(6, 12), rep_seconds=3.0,
      steps=(
          "Lie under a solid table, chest below the edge, and grip it shoulder-width.",
          "Straighten your legs so only your heels touch the floor.",
          "Brace into a straight line from head to heels.",
          "Pull your chest to the edge, pause, and lower to straight arms.",
      ),
      cues=("Body like a plank", "Elbows to your pockets", "Pause at the top"),
      mistakes=("Hips piking or sagging.", "Half reps that stop short of the table."),
      easier=("table_row_bent",), similar=("table_chin_row",)),

    S("table_chin_row", "Underhand Table Row", "underhand-grip-inverted-back-row", "back",
      muscles=("Lats", "Biceps", "Upper back"),
      purpose="Palms facing you shifts the row toward your lats and biceps — "
              "your best biceps builder without dumbbells.",
      needs=("table",), reps=(6, 12), rep_seconds=3.0,
      steps=(
          "Lie under a solid table and grip the edge with your palms facing you, hands shoulder-width.",
          "Bend your knees to make it easier, or straighten them to make it harder.",
          "Pull your chest to the edge, keeping your elbows close to your sides.",
          "Lower slowly to straight arms.",
      ),
      cues=("Elbows close to your ribs", "Lower for two seconds"),
      mistakes=("Elbows flaring out.", "Dropping quickly at the bottom."),
      similar=("table_row",)),

    S("door_row", "Door Row", "bodyweight-row-door-handle", "back",
      muscles=("Upper back", "Lats", "Biceps"),
      purpose="A row you can do anywhere with a door. Walk your feet closer "
              "to the door to make it harder.",
      reps=(10, 15), rep_seconds=3.0,
      steps=(
          "Use a solid door with firmly fixed handles. Open it and stand facing its edge.",
          "Grip both handles (or a towel looped around them), feet close to the bottom of the door.",
          "Lean back until your arms are straight, body in a straight line.",
          "Pull your chest to the door edge, squeezing your shoulder blades, then lower slowly.",
      ),
      cues=("Test it with a gentle lean first", "Squeeze your shoulder blades", "Straight body"),
      mistakes=("Using a loose handle or a door that can swing shut.",
                "Bending at the hips instead of pulling with your back."),
      harder=("table_row_bent",), similar=("table_row_bent",)),

    S("floor_pulldown", "Towel Floor Pulldown", "sliding-floor-pulldown-on-towel", "back",
      muscles=("Lats", "Core", "Triceps (long head)"),
      purpose="Without a bar, this is the closest thing to a lat pulldown: "
              "slide out long, then pull yourself back with your lats.",
      reps=(8, 15), rep_seconds=3.5,
      steps=(
          "Kneel on all fours on a smooth floor with both hands on a folded towel.",
          "Slide the towel forward, lowering your chest toward the floor, as far as you can control.",
          "Press the towel into the floor and pull it back toward your knees with straight arms.",
          "Think of pulling with your armpits, not your hands.",
      ),
      cues=("Press down and pull back", "Ribs down, back flat", "Only as far as you control"),
      mistakes=("Sliding so far your lower back sags.", "Bending your elbows to cheat the pull."),
      similar=("table_row_bent",)),

    # ------------------------------------------------------------- shoulders
    S("elevated_pike", "Feet-Up Pike Push-Up", "pike-push-up-on-bench-version-2", "shoulders",
      muscles=("Shoulders", "Triceps", "Upper chest"),
      purpose="Feet on a chair puts more of your weight over your hands — a "
              "harder bodyweight overhead press.",
      needs=("bench",), reps=(5, 10), rep_seconds=3.0,
      steps=(
          "Put your feet on a sturdy chair and your hands on the floor, shoulder-width.",
          "Walk your hands back and lift your hips until your upper body is close to vertical.",
          "Bend your elbows to lower the top of your head toward the floor in front of your hands.",
          "Push back up to straight arms.",
      ),
      cues=("Hips over your shoulders", "Head and hands make a triangle"),
      mistakes=("Hips drifting back down into a decline push-up.",
                "Elbows flaring straight out to the sides."),
      easier=("pike_pushup",)),

    S("prone_t_raise", "Prone T Raise", "lying-t-raise", "shoulders",
      muscles=("Rear shoulders", "Mid back"),
      purpose="Rear shoulders and the muscles between your shoulder blades, "
              "for balance against all the push-ups.",
      reps=(12, 20), rep_seconds=3.0,
      steps=(
          "Lie face down, arms straight out to the sides like a T, thumbs pointing up.",
          "Rest your forehead on a folded towel so your neck stays long.",
          "Squeeze your shoulder blades together and lift your arms off the floor.",
          "Hold one second at the top, then lower slowly.",
      ),
      cues=("Squeeze your shoulder blades", "Thumbs up", "Hold at the top"),
      mistakes=("Lifting your chest instead of your arms.", "Shrugging up toward your ears."),
      similar=("rear_delt_fly",)),

    # ------------------------------------------------------------------ arms
    S("towel_curl", "Towel Curl (leg as weight)", "lying-biceps-curl-with-towel", "arms",
      muscles=("Biceps", "Forearms"),
      purpose="Your leg becomes the dumbbell. Let the leg go heavier or "
              "lighter until the last reps are hard.",
      reps=(10, 15), rep_seconds=3.0,
      steps=(
          "Lie on your back and loop a towel behind one thigh, just above the knee. Hold both ends, palms up.",
          "Let that leg hang heavy with your elbows by your sides.",
          "Curl the towel toward your shoulders, lifting the leg with your arms only.",
          "Lower slowly. Use the other leg on the next set.",
      ),
      cues=("Elbows pinned to your sides", "The leg stays heavy", "Lower slowly"),
      mistakes=("Lifting the leg with your hip instead of your arms.",
                "Letting your elbows drift up."),
      similar=("table_chin_row",)),

    S("kneeling_triceps_ext", "Kneeling Triceps Extension", "bodyweight-kneeling-triceps-extension", "arms",
      muscles=("Triceps",),
      purpose="A bodyweight skull crusher: push from your forearms up onto "
              "your hands. Move your knees back to make it harder.",
      reps=(8, 15), rep_seconds=3.0,
      steps=(
          "Kneel and put your forearms on the floor, elbows under your shoulders, hands forward.",
          "Brace your stomach so your body is straight from head to knees.",
          "Press through your palms to straighten your arms, lifting your forearms off the floor.",
          "Lower slowly back onto your forearms.",
      ),
      cues=("Elbows stay narrow", "Straight from head to knees", "Slow on the way down"),
      mistakes=("Hips piking up to make it easier.", "Elbows flaring out."),
      similar=("diamond_pushup", "bench_dip")),

    # ------------------------------------------------------------------ legs
    S("pistol_box", "Single-Leg Squat to Chair", "pistol-squat-to-box", "legs",
      muscles=("Quads", "Glutes"),
      purpose="All your weight on one leg is real strength work, no dumbbells "
              "needed. The chair sets the depth and catches you.",
      needs=("bench",), per_side=True, reps=(5, 10), rep_seconds=3.5,
      steps=(
          "Stand in front of a sturdy chair and lift one foot slightly off the floor.",
          "Reach your arms forward and sit back slowly onto the chair on one leg.",
          "Touch the seat lightly — do not flop — and stand back up on the same leg.",
          "Finish all reps, then switch legs. Use a higher seat if you cannot stand up yet.",
      ),
      cues=("Sit back slowly", "Knee over your toes", "Push the floor away"),
      mistakes=("Dropping onto the chair and rocking up.", "Knee caving inward."),
      easier=("box_squat",), similar=("bw_bss",)),

    S("bw_split_squat", "Split Squat (bodyweight)", "split-squat", "legs",
      muscles=("Quads", "Glutes"),
      purpose="Single-leg work on the floor. Lower slowly — three seconds "
              "down — once the reps get easy.",
      tracker="lunge", view="side", per_side=True, reps=(10, 15), rep_seconds=3.0,
      steps=(
          "Take a long step forward and lift your back heel.",
          "Lower straight down until your back knee nearly touches the floor.",
          "Push up through your front foot. Finish all reps, then switch legs.",
      ),
      cues=("Straight down, not forward", "Torso tall"),
      mistakes=("Front knee caving in.", "Stance too short."),
      harder=("bw_bss",), similar=("bw_reverse_lunge",)),

    S("bw_bss", "Bulgarian Split Squat (bodyweight)", "assisted-bulgarian-split-squat", "legs",
      muscles=("Quads", "Glutes", "Adductors"),
      purpose="Back foot on a chair loads the front leg hard — the best leg "
              "builder there is without weights.",
      needs=("bench",), tracker="lunge", view="side", per_side=True, reps=(8, 15),
      rep_seconds=3.5,
      steps=(
          "Stand about two feet in front of a sturdy chair. Put the top of your back foot on the seat.",
          "Hold a wall or door frame lightly for balance if you need to.",
          "Lower until your front thigh is about parallel to the floor.",
          "Drive up through your front heel. Finish all reps, then switch legs.",
          "When 15 is easy, lower over three seconds and pause at the bottom.",
      ),
      cues=("Weight in the front heel", "Torso tall or slightly forward", "Slow on the way down"),
      mistakes=("Front foot too close to the chair.", "Pushing off the back foot."),
      easier=("bw_split_squat",), harder=("bss",), similar=("bw_reverse_lunge",)),

    S("bw_reverse_lunge", "Reverse Lunge (bodyweight)", "bodyweight-reverse-lunge", "legs",
      muscles=("Quads", "Glutes"),
      purpose="Stepping back is easier on the knees than stepping forward, "
              "and works the glutes more.",
      tracker="lunge", view="side", per_side=True, reps=(10, 15), rep_seconds=3.0,
      steps=(
          "Stand tall, feet hip-width.",
          "Step one foot back and lower until your back knee nearly touches the floor.",
          "Drive through your front foot to step back up.",
          "Finish all reps on one leg, then switch.",
      ),
      cues=("Step back, drop straight down", "Front knee tracks your toes"),
      mistakes=("Short steps that push the front knee far forward.", "Wobbling — slow down."),
      harder=("bw_bss",), similar=("bw_split_squat",)),

    S("bw_step_up", "Step-Up (bodyweight)", "step-up", "legs",
      muscles=("Quads", "Glutes"),
      purpose="Single-leg strength onto a sturdy chair or step.",
      needs=("bench",), per_side=True, reps=(10, 15), rep_seconds=3.0,
      steps=(
          "Stand facing a sturdy chair or step that does not slide. Put one whole foot on it.",
          "Push through that heel to stand up on it. Do not push off the back foot.",
          "Step down slowly with the other foot. Finish all reps, then switch legs.",
      ),
      cues=("Drive through the top heel", "Step down slowly"),
      mistakes=("Pushing off the bottom foot.", "A chair that can slide or tip."),
      similar=("bw_reverse_lunge",)),

    S("bw_calf_raise", "Single-Leg Calf Raise (bodyweight)", "standing-calf-raise", "legs",
      muscles=("Calves",),
      purpose="Calves respond to a full stretch and a pause at the top.",
      per_side=True, reps=(12, 25), rep_seconds=2.5,
      steps=(
          "Stand on one foot with the ball of the foot on a step or a thick book, heel hanging off.",
          "Hold a wall for balance.",
          "Lower your heel as far as it goes, then rise as high as you can.",
          "Pause one second at the top. Finish all reps, then switch.",
      ),
      cues=("Full stretch at the bottom", "Pause at the top"),
      mistakes=("Bouncing through short reps.",)),

    S("wall_sit", "Wall Sit", "sit-wall", "legs",
      muscles=("Quads",),
      purpose="A thigh burner you can do anywhere there is a wall.",
      hold=True, reps=(30, 60), seconds=30,
      steps=(
          "Lean your back flat against a wall and walk your feet forward.",
          "Slide down until your thighs are parallel to the floor, knees over your ankles.",
          "Hold, breathing steadily.",
      ),
      cues=("Thighs parallel", "Back flat on the wall"),
      mistakes=("Sitting too high.", "Knees drifting past your toes."),
      similar=("bw_squat",)),

    # ---------------------------------------------------------------- glutes
    S("bw_sl_rdl", "Single-Leg Romanian Deadlift (bodyweight)", "bodyweight-single-leg-deadlift", "glutes",
      muscles=("Hamstrings", "Glutes", "Balance"),
      purpose="Hamstrings and glutes on one leg — balance does a lot of the "
              "work while there is no weight.",
      tracker="hinge", view="side", per_side=True, reps=(10, 15), rep_seconds=3.5,
      steps=(
          "Stand on one leg with a soft knee.",
          "Hinge forward, reaching your hands toward the floor while the free leg lifts straight behind you.",
          "Go until you feel a stretch in the standing hamstring and your body is nearly parallel to the floor.",
          "Squeeze your glute to stand up. Finish all reps, then switch.",
      ),
      cues=("Hips square to the floor", "Long line from head to heel", "Slow on the way down"),
      mistakes=("Rounding your back to reach lower.", "Hips opening to the side."),
      similar=("towel_leg_curl",)),

    S("towel_leg_curl", "Towel Hamstring Curl", "sliding-leg-curl-on-floor-with-towel", "glutes",
      muscles=("Hamstrings", "Glutes"),
      purpose="A leg curl with no machine: heels on a towel on a smooth floor. "
              "Do it one leg at a time once both legs is easy.",
      reps=(8, 15), rep_seconds=3.5,
      steps=(
          "Lie on your back on a smooth floor, heels on a folded towel, knees bent.",
          "Lift your hips into a bridge.",
          "Keeping your hips up, slide your heels out until your legs are nearly straight.",
          "Pull your heels back toward your hips. Hips stay up the whole set.",
      ),
      cues=("Hips stay high", "Slow on the way out"),
      mistakes=("Dropping your hips as your legs straighten.", "Rushing the slide out."),
      easier=("glute_bridge",), similar=("bw_sl_rdl",)),
)
