import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import app
from ads import mark_match_outcome


def main():
    completed = {}
    abandoned = {}
    complete_break = mark_match_outcome(completed, "possession", "completed_board", "match-complete")
    abandoned_break = mark_match_outcome(abandoned, "possession", "abandoned_forfeit", "match-abandoned")

    assert complete_break["eligible"] is True
    assert complete_break["timeout_ms"] == 5000
    assert abandoned_break["eligible"] is False

    room_state = app.create_match_state()
    mark_match_outcome(room_state, "possession", "completed_board", "serialized-match")
    room = {"state": room_state, "player_names": {1: "A", 2: "B"}}
    assert app.serialize_room_state(room)["ad_break"]["eligible"] is True

    with app.app.test_client() as client:
        response = client.get("/ads/client.js")
        source = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "window.MatchAds" in source
        assert "Math.min(5000" in source
        assert response.headers["Cache-Control"] == "no-store"

        provider_response = client.get("/ads/native-provider.js")
        provider_source = provider_response.get_data(as_text=True)
        assert provider_response.status_code == 200
        assert "window.FootballAdProvider" in provider_source
        assert "registerPlugin?.('AdMob')" in provider_source
        assert "prepareInterstitial" in provider_source
        assert "showInterstitial" in provider_source
        assert "requestConsentInfo" in provider_source
        assert "showPrivacyOptionsForm" in provider_source
        assert "ca-app-pub-3940256099942544/4411468910" in provider_source
        assert provider_response.headers["Cache-Control"] == "no-store"
        syntax = subprocess.run(
            ["node", "--check", "-"], input=provider_source,
            text=True, capture_output=True, check=False,
        )
        assert syntax.returncode == 0, syntax.stderr

    print({
        "completed_match_has_ad": True,
        "abandoned_match_skips_ad": True,
        "five_second_ceiling": True,
        "isolated_ads_module": True,
        "native_admob_provider": True,
    })


if __name__ == "__main__":
    main()
