import json


def make_button(
    label: str, payload: str, color: str = "secondary", type_="text"
) -> dict:
    res = {
        "action": {
            "type": "text" if type_ is None else type_,
            "payload" if type_ == "text" else "link": payload,
            "label": label,
        }
    }
    if type_ == "text":
        res["color"] = color if color is not None else "secondary"
    return res


def make_keyboard(buttons: list, to_mes: bool = False) -> str:
    keyboard = {"inline": to_mes, "buttons": []}
    for level in buttons:
        for list_btn in level:
            btns = []
            for param in list_btn:
                btns.append(
                    make_button(
                        param[0],
                        param[1],
                        param[2] if len(param) == 3 else "secondary",
                        param[3] if len(param) == 4 else "text",
                    )
                )
            keyboard["buttons"].append(btns)
    return json.dumps(keyboard, ensure_ascii=False)