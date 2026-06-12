"""Reviewer edge-case probes run against whichever candidate is currently applied.
Imports the package, exercises subtle cases, prints PASS/FAIL lines. Pure stdlib.
"""
import importlib, sys, random

# Fresh import each run
for m in list(sys.modules):
    if m.startswith("word_garden"):
        del sys.modules[m]
from word_garden import game, words

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))

GS = game.GameState

def mk(secret, guessed=(), water=6, weeds=0, maxw=6, over=False, won=False, msg=""):
    return GS(secret_word=secret, guessed_letters=set(guessed), remaining_water=water,
              weed_count=weeds, max_water=maxw, status_message=msg, game_over=over, won=won)

# 1. Win on last unit of water: water=1, make final CORRECT guess -> win, not loss
s = mk("CAT", guessed={"C","A"}, water=1, weeds=5)
r = game.apply_guess(s, "T")
check("win_on_last_water:won", r.won is True, f"won={r.won}")
check("win_on_last_water:game_over", r.game_over is True)
check("win_on_last_water:not_loss_msg", "ran out" not in r.status_message.lower(), f"msg={r.status_message!r}")
check("win_on_last_water:is_lost_false", game.is_lost(r) is False)

# 2. Terminal guess status_message is win text, not "Good guess!"
s = mk("CAT", guessed={"C","A"}, water=6)
r = game.apply_guess(s, "T")
check("win_msg_not_goodguess", r.status_message != game.__dict__.get("MSG_CORRECT_GUESS", game.__dict__.get("MSG_CORRECT","")), f"msg={r.status_message!r}")
check("win_msg_nonempty", bool(r.status_message))

# 3. Terminal loss guess message is loss text, not "No match."
s = mk("GARDEN", guessed={"Z"}, water=1, weeds=1)
r = game.apply_guess(s, "X")
wrong = game.__dict__.get("MSG_WRONG_GUESS", game.__dict__.get("MSG_WRONG",""))
check("loss_msg_not_nomatch", r.status_message != wrong, f"msg={r.status_message!r}")
check("loss_water_zero", r.remaining_water == 0)

# 4. Repeated guess after game over -> no-op with message; counters unchanged
s = mk("GARDEN", guessed=set("GARDEN"), water=4, weeds=2, over=True, won=True)
r = game.apply_guess(s, "Q")
check("after_over_water_unchanged", r.remaining_water == 4, f"w={r.remaining_water}")
check("after_over_weeds_unchanged", r.weed_count == 2)
check("after_over_Q_not_recorded", "Q" not in r.guessed_letters)
check("after_over_still_over", r.game_over is True)

# 5. Multi-occurrence reveal
s = mk("SEEDLING", guessed={"E"})
disp = game.display_word(s)
parts = disp.split()
check("multi_occurrence_reveal", parts[1]=="E" and parts[2]=="E" and parts[0]=="_", f"disp={disp!r}")

# 6. Repeated WRONG guess does not double-penalize
s = mk("GARDEN", guessed=set(), water=6, weeds=0)
r = game.apply_guess(s, "Z")
r2 = game.apply_guess(r, "Z")
check("repeat_wrong_no_double_penalty", r2.remaining_water == 5 and r2.weed_count == 1, f"w={r2.remaining_water} weeds={r2.weed_count}")

# 7. select_word every difficulty + unknown raises
for d, lo, hi in [("easy",4,6),("normal",5,8),("hard",7,99)]:
    rng = random.Random(0)
    ok = True
    for _ in range(40):
        w = words.select_word(d, rng=rng)
        if not (w in words.WORDS and lo <= len(w) <= hi):
            ok = False; break
    check(f"select_{d}_valid", ok)
try:
    words.select_word("nope")
    check("select_unknown_raises", False)
except ValueError:
    check("select_unknown_raises", True)
except Exception as e:
    check("select_unknown_raises", False, f"raised {type(e).__name__}")

# 8. Empty pool path: temporarily shrink WORDS so 'hard' (7+) is empty
orig = words.WORDS[:]
try:
    words.WORDS[:] = ["CAT","DOG"]  # nothing >=7
    try:
        words.select_word("hard", rng=random.Random(0))
        check("empty_pool_raises", False, "returned a word")
    except ValueError:
        check("empty_pool_raises", True)
    except Exception as e:
        check("empty_pool_raises", False, f"raised {type(e).__name__}")
finally:
    words.WORDS[:] = orig

# 9. validate ordering: lowercase normalize, digit, symbol, empty, multi
checks = {
    "a": ("A",""),
}
l,m = game.validate_guess("a"); check("validate_lower", l=="A" and m=="")
l,m = game.validate_guess("  z  "); check("validate_strip", l=="Z" and m=="")
l,m = game.validate_guess(""); check("validate_empty", l is None and m!="")
l,m = game.validate_guess("ab"); check("validate_multi", l is None and m!="")
l,m = game.validate_guess("7"); check("validate_digit", l is None and m!="")
l,m = game.validate_guess("!"); check("validate_symbol", l is None and m!="")

# 10. new_game does not mutate; default normal water=6, max==remaining
g = game.new_game("normal", rng=random.Random(3))
check("new_game_water6", g.remaining_water==6 and g.max_water==6)
check("new_game_uppercase", g.secret_word == g.secret_word.upper())
check("new_game_empty_guess", g.guessed_letters == set())

# 11. is_lost win-precedence at water 0 with full reveal
s = mk("GO", guessed={"G","O"}, water=0)
check("is_lost_false_when_won_water0", game.is_lost(s) is False)
check("is_won_true_water0", game.is_won(s) is True)

# 12. display_word exact format
s = mk("GARDEN", guessed={"G","R","E"})
check("display_format", game.display_word(s) == "G _ R _ E _", repr(game.display_word(s)))

fails = [r for r in results if not r[1]]
for name, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
print(f"\nSUMMARY: {len(results)-len(fails)}/{len(results)} passed")
