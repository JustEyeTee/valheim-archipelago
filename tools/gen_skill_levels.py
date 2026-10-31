"""Adds a skill check row to mod/checks.tsv for every level 1-100 of every skill that has any, copying the
skill's tier and requirements from its existing rows; skill_check_spacing picks which levels a seed uses.
New rows go at the end of the file, so the location ids of existing rows don't change.
Run from the repo root (then tools/gen_check_biomes.py and tools/gen_apworld_data.py):  python3 tools/gen_skill_levels.py
"""
import pathlib

path = pathlib.Path(__file__).resolve().parent.parent / "mod" / "checks.tsv"
lines = path.read_text().rstrip("\n").split("\n")
skills = {}  # game skill -> (display name, tier, requirements, levels present), in file order
for line in lines:
    cols = line.split("\t")
    if line.startswith("#") or cols[0] != "skill":
        continue
    skill, level = cols[1].split(":")
    name = cols[2][len("Skill: "):].rsplit(" ", 1)[0]
    entry = skills.setdefault(skill, (name, cols[3], cols[4], set()))
    entry[3].add(int(level))
added = [f"skill\t{skill}:{level}\tSkill: {name} {level}\t{tier}\t{reqs}"
         for skill, (name, tier, reqs, have) in skills.items() for level in range(1, 101) if level not in have]
path.write_text("\n".join(lines + added) + "\n")
print(f"added {len(added)} skill level rows for {len(skills)} skills")
