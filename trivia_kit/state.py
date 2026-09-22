"""Maps a saved EventConfig, or just a set of rounds, onto the Streamlit widget
keys used by app.py."""


def mc_options_to_text(mc_options):
    """A Multiple Choice round's resolved options as the fallback textarea shows
    them: one line per question, its choices comma-separated."""
    return "\n".join(", ".join(opts) for opts in mc_options)


def mc_options_from_text(text):
    """The reverse of `mc_options_to_text`: one tuple of choices per line, in
    question order. A blank line means that question has no options yet."""
    return tuple(tuple(o.strip() for o in line.split(",") if o.strip()) for line in text.splitlines())


def state_from_rounds(rounds):
    """The session-state entries for a sequence of Round, keyed by position (the
    per-round widget keys app.py uses: name_0, type_0, q_0, ...). Shared by a full
    setup load and a rounds-only import, so both fill in rounds the same way."""
    state = {}
    for i, rnd in enumerate(rounds):
        state[f"name_{i}"] = rnd.name
        state[f"type_{i}"] = rnd.kind
        state[f"q_{i}"] = rnd.questions
        state[f"pts_{i}"] = rnd.points
        state[f"extra_{i}"] = rnd.extra
        state[f"choices_{i}"] = rnd.choices
        state[f"pics_saved_{i}"] = rnd.images
        state[f"mc_opts_{i}"] = mc_options_to_text(rnd.mc_options)
    return state


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
    state.update(state_from_rounds(config.rounds))
    return state
