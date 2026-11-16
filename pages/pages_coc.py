from components import common_ui as common

# ==========================================
# クトゥルフ神話TRPG（通常版）
# ==========================================
def _load():
    from systems.coc import app_coc, profile_coc
    return lambda: app_coc.main(profile_coc.STANDARD)

common.run_page(_load)
