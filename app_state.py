"""Maps a saved EventConfig onto the Streamlit widget keys used by app.py."""


def state_from_config(config):
    """The session-state entries that make the app show `config`."""
    state = {
        "event_title": config.title,
        "event_date": config.date,
        "event_venue": config.venue,
        "logo_saved": config.logo,
        "paper": config.paper,
        "layout": config.layout,
        "ink_saver": config.ink_saver,
        "team_mode": config.team_mode,
        "num_teams": config.num_teams,
        "team_names": "\n".join(config.team_names),
        "packet_order": config.packet_order,
        "questions_csv": config.questions_csv,
        "num_rounds": len(config.rounds),
    }
    for i, rnd in enumerate(config.rounds):
        state[f"name_{i}"] = rnd.name
        state[f"type_{i}"] = rnd.kind
        state[f"q_{i}"] = rnd.questions
        state[f"pts_{i}"] = rnd.points
        state[f"extra_{i}"] = rnd.extra
        state[f"choices_{i}"] = rnd.choices
        state[f"pics_saved_{i}"] = rnd.images
    return state
