
import csv
import json

from dataclasses import (
    dataclass,
    field,
)

from pathlib import Path

from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
)


# =========================================================
# CAMPOS DISPONÍVEIS
# =========================================================

EXPORT_FIELDS = {
    "name": "Nome",
    "printed_name": "Nome impresso",
    "mana_cost": "Custo de mana",
    "type_line": "Tipo",
    "oracle_text": "Texto / efeito",
    "power": "Poder",
    "toughness": "Resistência",
    "power_toughness": "Poder / Resistência",
    "loyalty": "Lealdade",
    "defense": "Defesa",
    "quantity": "Quantidade",
    "set_name": "Edição",
    "set_code": "Código da edição",
    "collector_number": "Número coletor",
    "lang": "Idioma",
    "scryfall_id": "Scryfall ID",
    "image_url": "URL da imagem",
    "image_path": "Caminho da imagem",
}


DEFAULT_FIELDS = [
    "name",
    "mana_cost",
    "type_line",
    "oracle_text",
    "power_toughness",
    "quantity",
    "set_name",
    "collector_number",
]


PRESETS = {
    "Coleção completa": [
        "name",
        "printed_name",
        "mana_cost",
        "type_line",
        "oracle_text",
        "power",
        "toughness",
        "loyalty",
        "defense",
        "quantity",
        "set_name",
        "set_code",
        "collector_number",
        "lang",
        "scryfall_id",
        "image_url",
    ],

    "Essencial": DEFAULT_FIELDS,

    "Planilha": [
        "name",
        "quantity",
        "set_name",
        "set_code",
        "collector_number",
        "mana_cost",
        "type_line",
        "power_toughness",
        "lang",
    ],

    "Identificação": [
        "name",
        "set_name",
        "set_code",
        "collector_number",
        "lang",
        "scryfall_id",
    ],
}


# =========================================================
# HELPERS
# =========================================================

def _value(
    card: Dict[str, Any],
    key: str,
    default: Any = "—",
) -> Any:

    value = card.get(
        key
    )

    if value is None or value == "":
        return default

    return value


# =========================================================
# NOME DA CARTA
# =========================================================

def _localized_name(
    card: Dict[str, Any],
) -> Any:
    """
    Retorna o nome localizado da carta para exibição/exportação.

    A ordem de prioridade é:

        1. printed_name
        2. localized_name
        3. name_localized
        4. nome_localizado
        5. nome
        6. name
        7. nome da primeira face localizada
        8. "—"

    O campo `name` continua sendo o fallback oficial em inglês.
    Assim, os presets e as exportações personalizadas usam exatamente
    a mesma resolução de nome.
    """

    # -----------------------------------------------------
    # Campos de localização mais comuns
    # -----------------------------------------------------

    localized_keys = (
        "printed_name",
        "localized_name",
        "name_localized",
        "nome_localizado",
        "nome",
    )

    for key in localized_keys:

        value = card.get(
            key
        )

        if (
            value is not None
            and str(value).strip()
        ):
            return value

    # -----------------------------------------------------
    # Cartas de duas faces
    # -----------------------------------------------------

    faces = card.get(
        "card_faces"
    )

    if isinstance(
        faces,
        list,
    ):

        for face in faces:

            if not isinstance(
                face,
                dict,
            ):
                continue

            for key in localized_keys:

                value = face.get(
                    key
                )

                if (
                    value is not None
                    and str(value).strip()
                ):
                    return value

    # -----------------------------------------------------
    # Fallback: nome original do Scryfall
    # -----------------------------------------------------

    name = card.get(
        "name"
    )

    if (
        name is not None
        and str(name).strip()
    ):
        return name

    return "—"

def _quantity(
    card: Dict[str, Any],
) -> int:

    try:

        return int(
            card.get(
                "quantity",
                0,
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        return 0


def _power_toughness(
    card: Dict[str, Any],
) -> str:

    power = card.get(
        "power"
    )

    toughness = card.get(
        "toughness"
    )

    if (
        power in (
            None,
            "",
        )
        and toughness in (
            None,
            "",
        )
    ):

        return "—"

    power = (
        power
        if power not in (
            None,
            "",
        )
        else "?"
    )

    toughness = (
        toughness
        if toughness not in (
            None,
            "",
        )
        else "?"
    )

    return f"{power}/{toughness}"


def _field_value(
    card: Dict[str, Any],
    field: str,
) -> Any:

    # -----------------------------------------------------
    # NOME
    # -----------------------------------------------------

    if field == "name":

        return _localized_name(
            card
        )

    # -----------------------------------------------------
    # NOME IMPRESSO
    # -----------------------------------------------------

    if field == "printed_name":

        return _value(
            card,
            "printed_name",
        )

    # -----------------------------------------------------
    # QUANTIDADE
    # -----------------------------------------------------

    if field == "quantity":

        return _quantity(
            card
        )

    # -----------------------------------------------------
    # PODER / RESISTÊNCIA
    # -----------------------------------------------------

    if field == "power_toughness":

        return _power_toughness(
            card
        )

    # -----------------------------------------------------
    # DEMAIS CAMPOS
    # -----------------------------------------------------

    return _value(
        card,
        field,
    )


def _card_faces(
    card: Dict[str, Any],
) -> Optional[
    List[
        Dict[str, Any]
    ]
]:

    faces = card.get(
        "card_faces"
    )

    if not faces:
        return None

    treated = []

    for face in faces:

        # -------------------------------------------------
        # Nome localizado da face
        # -------------------------------------------------

        face_printed_name = (
            face.get(
                "printed_name"
            )
        )

        face_name = (
            face_printed_name
            if (
                face_printed_name
                and str(
                    face_printed_name
                ).strip()
            )
            else face.get(
                "name",
                "—",
            )
        )

        treated.append(
            {
                "nome": face_name,

                "mana": _value(
                    face,
                    "mana_cost",
                ),

                "tipo": _value(
                    face,
                    "type_line",
                ),

                "efeito": _value(
                    face,
                    "oracle_text",
                ),

                "power": _value(
                    face,
                    "power",
                ),

                "toughness": _value(
                    face,
                    "toughness",
                ),

                "lealdade": _value(
                    face,
                    "loyalty",
                ),

                "imagem": _value(
                    face,
                    "image_uris",
                    None,
                ),
            }
        )

    return treated


# =========================================================
# CONFIGURAÇÃO
# =========================================================

@dataclass
class ExportConfig:

    format: str = "csv"

    fields: List[str] = field(
        default_factory=lambda:
        list(
            DEFAULT_FIELDS
        )
    )

    separator: str = ","

    encoding: str = "utf-8-sig"

    include_header: bool = True

    include_summary: bool = False

    card_separator: str = "\n"

    title: str = "MINHA COLEÇÃO — MAGIC"

    field_separator: str = ": "

    pretty_json: bool = True

    def normalized(
        self,
    ) -> "ExportConfig":

        valid = set(
            EXPORT_FIELDS
        )

        fields = [
            field_name
            for field_name
            in self.fields
            if field_name in valid
        ]

        if not fields:

            fields = list(
                DEFAULT_FIELDS
            )

        return ExportConfig(
            format=str(
                self.format
                or "csv"
            ).lower(),

            fields=fields,

            separator=(
                self.separator
                or ","
            ),

            encoding=(
                self.encoding
                or "utf-8-sig"
            ),

            include_header=bool(
                self.include_header
            ),

            include_summary=bool(
                self.include_summary
            ),

            card_separator=(
                self.card_separator
                or "\n"
            ),

            title=(
                self.title
                or "MINHA COLEÇÃO — MAGIC"
            ),

            field_separator=(
                self.field_separator
                or ": "
            ),

            pretty_json=bool(
                self.pretty_json
            ),
        )


# =========================================================
# PRESETS
# =========================================================

def get_all_export_presets(
) -> Dict[str, List[str]]:

    result = {
        name: list(
            fields
        )

        for name, fields
        in PRESETS.items()
    }

    for name, fields in (
        _load_custom_presets()
        .items()
    ):

        result[name] = list(
            fields
        )

    return result


def config_from_preset(
    preset_name: str,
    format_name: str = "csv",
) -> ExportConfig:

    presets = (
        get_all_export_presets()
    )

    fields = presets.get(
        preset_name,
        list(
            DEFAULT_FIELDS
        ),
    )

    return ExportConfig(
        format=format_name,
        fields=list(
            fields
        ),
    )


def save_export_preset(
    name: str,
    config: ExportConfig,
) -> bool:

    name = str(
        name or ""
    ).strip()

    if not name:
        return False

    data = (
        _load_custom_presets()
    )

    data[name] = list(
        config
        .normalized()
        .fields
    )

    return _save_custom_presets(
        data
    )


def delete_export_preset(
    name: str,
) -> bool:

    if name in PRESETS:
        return False

    data = (
        _load_custom_presets()
    )

    if name not in data:
        return False

    del data[
        name
    ]

    return _save_custom_presets(
        data
    )


def _preset_path() -> Path:

    path = (
        Path(__file__)
        .resolve()
        .parent
        .parent
        / "data"
    )

    path.mkdir(
        parents=True,
        exist_ok=True,
    )

    return (
        path
        / "export_presets.json"
    )


def _load_custom_presets(
) -> Dict[str, List[str]]:

    path = _preset_path()

    if not path.exists():
        return {}

    try:

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            data,
            dict,
        ):
            return {}

        result = {}

        for name, fields in (
            data.items()
        ):

            if (
                isinstance(
                    name,
                    str,
                )
                and isinstance(
                    fields,
                    list,
                )
            ):

                result[name] = [
                    field_name
                    for field_name
                    in fields
                    if field_name
                    in EXPORT_FIELDS
                ]

        return result

    except Exception as error:

        print(
            "[EXPORT] Erro ao carregar presets:",
            error,
        )

        return {}


def _save_custom_presets(
    data: Dict[str, List[str]],
) -> bool:

    try:

        path = _preset_path()

        path.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=4,
            ),
            encoding="utf-8",
        )

        return True

    except Exception as error:

        print(
            "[EXPORT] Erro ao salvar preset:",
            error,
        )

        return False


# =========================================================
# EXPORTAÇÃO CUSTOMIZADA
# =========================================================

def export_collection_custom(
    filepath: str,
    cards: Iterable[
        Dict[str, Any]
    ],
    config: ExportConfig,
) -> None:

    config = (
        config.normalized()
    )

    cards = list(
        cards or []
    )

    path = Path(
        filepath
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if config.format == "csv":

        _export_csv(
            path,
            cards,
            config,
        )

        return

    if config.format == "json":

        _export_json(
            path,
            cards,
            config,
        )

        return

    if config.format == "txt":

        _export_txt(
            path,
            cards,
            config,
        )

        return

    raise ValueError(
        "Formato de exportação "
        f"não suportado: "
        f"{config.format}"
    )


# =========================================================
# CSV
# =========================================================

def _export_csv(
    path: Path,
    cards: List[
        Dict[str, Any]
    ],
    config: ExportConfig,
) -> None:

    with path.open(
        "w",
        encoding=config.encoding,
        newline="",
    ) as file:

        writer = csv.writer(
            file,
            delimiter=config.separator,
        )

        if config.include_header:

            writer.writerow(
                [
                    EXPORT_FIELDS[
                        field_name
                    ]

                    for field_name
                    in config.fields
                ]
            )

        for card in cards:

            writer.writerow(
                [
                    _field_value(
                        card,
                        field_name,
                    )

                    for field_name
                    in config.fields
                ]
            )


# =========================================================
# JSON
# =========================================================

def _export_json(
    path: Path,
    cards: List[
        Dict[str, Any]
    ],
    config: ExportConfig,
) -> None:

    result = []

    for card in cards:

        item = {}

        for field_name in (
            config.fields
        ):

            item[
                field_name
            ] = _field_value(
                card,
                field_name,
            )

        faces = _card_faces(
            card
        )

        if faces:

            item[
                "faces"
            ] = faces

        result.append(
            item
        )

    payload: Any = result

    if config.include_summary:

        total = sum(
            _quantity(
                card
            )

            for card in cards
        )

        payload = {

            "resumo": {

                "total_cartas":
                    total,

                "cartas_unicas":
                    len(cards),
            },

            "cartas":
                result,
        }

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=(
                4
                if config.pretty_json
                else None
            ),
        )


# =========================================================
# TXT
# =========================================================

def _export_txt(
    path: Path,
    cards: List[
        Dict[str, Any]
    ],
    config: ExportConfig,
) -> None:

    lines = []

    if config.title:

        lines.append(
            "═" * 62
        )

        lines.append(
            config.title
        )

        lines.append(
            "═" * 62
        )

        lines.append("")

    if config.include_summary:

        total = sum(
            _quantity(
                card
            )

            for card in cards
        )

        lines.append(
            f"Total de cartas: {total}"
        )

        lines.append(
            f"Cartas únicas: {len(cards)}"
        )

        lines.append("")

    for index, card in enumerate(
        cards
    ):

        if index > 0:

            lines.append(
                "─" * 62
            )

        for field_name in (
            config.fields
        ):

            label = (
                EXPORT_FIELDS[
                    field_name
                ]
            )

            value = _field_value(
                card,
                field_name,
            )

            lines.append(
                f"{label}"
                f"{config.field_separator}"
                f"{value}"
            )

    text = "\n".join(
        lines
    )

    path.write_text(
        text,
        encoding="utf-8",
    )

