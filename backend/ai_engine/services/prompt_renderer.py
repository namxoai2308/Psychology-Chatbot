from __future__ import annotations


def render_template(template: str, **variables: object) -> str:
    out = template
    for key, value in variables.items():
        out = out.replace("{" + key + "}", str(value))
    return out
