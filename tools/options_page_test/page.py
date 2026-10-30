"""Drives the Options Builder (docs/options/index.html) through cases and saves each case's YAML and
summary rows ("Checks", "Items") to <out>/cases.json, for check.py."""
import json, sys
from playwright.sync_api import sync_playwright
url, out = sys.argv[1], sys.argv[2]
TRAPS = "#opt-excluded_traps-"
cases = [
    ("kall_fimbulbringer", []),
    ("eikthyr", [("check", "#opt-goal_conditions-Relic-Hunt"), ("num", "#opt-relic_hunt_total", "50"),
                 ("num", "#opt-trap_percentage", "33"), ("num", "#opt-boost_percentage", "50")]),
    ("the_elder", [("check", "#opt-kill_checks"), ("num", "#opt-skill_checks", "100"), ("all_traps",), ("num", "#opt-comfort_checks", "3"),
                   ("uncheck", "#opt-starter_kit")]),
    ("yagluth", [("check", "#opt-goal_conditions-Relic-Hunt"), ("num", "#opt-relic_hunt_total", "37"),
                 ("num", "#opt-exploration_checks", "20"), ("click", "label[for=opt-exploration_check_spacing-half_percent]")]),
    ("moder", [("uncheck", "#opt-gear_items"), ("uncheck", "#opt-boss_items"), ("num", "#opt-trap_percentage", "50"),
               ("num", "#opt-boost_percentage", "50")]),
    ("eikthyr", [("uncheck", "#opt-biome_checks"), ("uncheck", "#opt-obtain_checks"), ("uncheck", "#opt-discovery_checks"),
                 ("uncheck", "#opt-build_checks"), ("uncheck", "#opt-eat_checks"), ("num", "#opt-skill_checks", "0"),
                 ("num", "#opt-exploration_checks", "0")]),
]
results, errors = [], []
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url, wait_until="networkidle")
    for goal, actions in cases:
        page.click("#reset"); page.click(f"label[for=opt-goal-{goal}]")
        for a in actions:
            if a[0] == "check": page.check(a[1])
            elif a[0] == "uncheck": page.uncheck(a[1])
            elif a[0] == "click": page.click(a[1])
            elif a[0] == "all_traps":
                for c in page.locator(f'input[id^="{TRAPS[1:]}"]').all(): c.check()
            else: page.fill(a[1], a[2]); page.dispatch_event(a[1], "change")
        groups = {}
        for div in page.locator("#summary > div").all():
            title = div.locator("h3").inner_text().split(" (")[0]
            dts, dds = div.locator("dt").all_inner_texts(), div.locator("dd").all_inner_texts()
            groups[title] = {k: int(v) for k, v in zip(dts, dds)}
        results.append({"goal": goal, "yaml": page.inner_text("#yaml"), "summary": groups,
                        "total": page.inner_text("#total")})
    b.close()
json.dump(results, open(f"{out}/cases.json", "w"), indent=1)
print(len(results), "cases; errors:", errors or "none")
