"""
SERVIÇO DE MOEDAS
=================

Camada centralizada de conversão e formatação de valores
do Magic Collection.

Responsabilidades:

- Definir as moedas suportadas (BRL, USD, EUR, TIX).
- Manter as taxas de câmbio em cache (sem travar a interface).
- Converter valores em USD para a moeda selecionada.
- Formatar valores no padrão brasileiro.
- Persistir a moeda escolhida pelo usuário (QSettings).

IMPORTANTE:

- Nenhuma chamada de rede acontece na linha de execução da interface.
- A interface sempre usa a última taxa conhecida.
- Se a atualização de taxas falhar, mantém a última taxa.
- A interface nunca quebra por causa de falha na cotação.
"""

from __future__ import annotations

import threading
import time

from PySide6.QtCore import QSettings

from components.card_details_dialog import (
    CACHED_USD_BRL,
    DEFAULT_USD_BRL,
)


# =========================================================
# MOEDAS SUPORTADAS
# =========================================================
#
# (código, símbolo, nome amigável)

CURRENCIES = (
    ("BRL", "R$", "Real"),
    ("USD", "US$", "Dólar"),
    ("EUR", "€", "Euro"),
    ("TIX", "Tix", "Tix"),
)

CURRENCY_SYMBOLS = {
    code: symbol
    for code, symbol, _ in CURRENCIES
}

# =========================================================
# TAXAS PADRÃO (FALLBACK)
# =========================================================
#
# Usadas somente quando não existe taxa em cache.
# Evitam que a interface mostre valores vazios.

DEFAULT_EUR_RATE = 0.92

# TIX é a moeda do Magic Online.
# O Scryfall guarda o preço em Tix por carta.
# Para a conversão de referência, consideramos 1 Tix ≈ 1 USD.

DEFAULT_TIX_RATE = 1.0

# Tempo de vida do cache de taxas (em segundos).
RATES_TTL = 3600.0

# Endpoint de cotações.
EXCHANGE_API_URL = (
    "https://economia.awesomeapi.com.br/json/last/"
)


# =========================================================
# SERVIÇO DE MOEDAS
# =========================================================


class CurrencyService:

    _lock = threading.Lock()

    # Taxas em relação ao USD.
    _rates = {
        "USD": 1.0,
        "BRL": float(CACHED_USD_BRL),
        "EUR": DEFAULT_EUR_RATE,
        "TIX": DEFAULT_TIX_RATE,
    }

    # Momento em que cada taxa foi obtida.
    _fetched_at: dict[str, float] = {}

    _background_started = False

    # =====================================================
    # SETTINGS
    # =====================================================

    _SETTINGS_KEY = "dashboard/currency"

    @staticmethod
    def get_selected_currency() -> str:
        settings = QSettings(
            "MagicCollection",
            "MagicCollection",
        )

        currency = settings.value(
            CurrencyService._SETTINGS_KEY,
            "BRL",
            type=str,
        )

        if currency not in CURRENCY_SYMBOLS:
            currency = "BRL"

        return currency

    @staticmethod
    def set_selected_currency(currency: str) -> None:
        if currency not in CURRENCY_SYMBOLS:
            return

        settings = QSettings(
            "MagicCollection",
            "MagicCollection",
        )

        settings.setValue(
            CurrencyService._SETTINGS_KEY,
            currency,
        )

    # =====================================================
    # TAXAS
    # =====================================================

    @staticmethod
    def rate(currency: str) -> float:
        """
        Retorna a taxa da moeda em relação ao USD.

        Nunca bloqueia a interface:
        usa a última taxa conhecida (ou o padrão).
        """

        currency = str(
            currency or "USD"
        ).upper()

        with CurrencyService._lock:

            rate = CurrencyService._rates.get(
                currency
            )

            if rate is None:
                return 1.0

            return float(rate)

    # =====================================================
    # ATUALIZAÇÃO EM SEGUNDO PLANO
    # =====================================================

    @classmethod
    def start_background_refresh(cls) -> None:
        """
        Inicia uma thread simples para atualizar as taxas
        em segundo plano, sem congelar a interface.
        """

        with cls._lock:

            if cls._background_started:
                return

            cls._background_started = True

        thread = threading.Thread(
            target=cls.refresh_rates_blocking,
            daemon=True,
        )

        thread.start()

    # =====================================================
    # ATUALIZAÇÃO BLOQUEANTE
    # =====================================================
    #
    # Só pode ser chamada fora da thread da interface
    # (thread de segundo plano ou testes).

    @classmethod
    def refresh_rates_blocking(cls) -> None:
        import requests

        results = {}

        for pair, key in (
            ("USD-BRL", "USDBRL"),
            ("USD-EUR", "USDEUR"),
        ):

            try:

                response = requests.get(
                    f"{EXCHANGE_API_URL}{pair}",
                    timeout=5,
                )

                response.raise_for_status()

                data = response.json()

                rate_data = data.get(
                    key,
                    {},
                )

                bid = rate_data.get(
                    "bid"
                )

                if bid in (
                    None,
                    "",
                ):
                    continue

                bid = float(bid)

                if bid <= 0:
                    continue

                if pair == "USD-BRL":
                    results["BRL"] = bid

                elif pair == "USD-EUR":
                    results["EUR"] = bid

            except Exception as error:

                print(
                    "[MOEDAS] Falha ao obter "
                    f"cotação {pair}:",
                    error,
                )

        if not results:
            return

        with cls._lock:

            now = time.monotonic()

            for currency, value in results.items():

                cls._rates[currency] = value

                cls._fetched_at[currency] = now

            # Mantém a cotação usada pelo restante do app.
            if "BRL" in results:

                import components.card_details_dialog as _details

                _details.CACHED_USD_BRL = results["BRL"]

            print(
                "[MOEDAS] Taxas atualizadas:",
                {
                    currency: round(
                        value,
                        4,
                    )
                    for currency, value in results.items()
                },
            )

    # =====================================================
    # CONVERSÃO
    # =====================================================

    @staticmethod
    def convert_usd(
        amount_usd,
        currency: str,
    ) -> float:
        """
        Converte um valor em USD para a moeda indicada.

        Retorna o valor convertido (float).
        """

        try:

            amount_usd = float(
                amount_usd
                or 0
            )

        except (
            TypeError,
            ValueError,
        ):

            amount_usd = 0.0

        currency = str(
            currency or "USD"
        ).upper()

        if currency == "USD":

            return amount_usd

        return (
            amount_usd
            * CurrencyService.rate(
                currency
            )
        )

    # =====================================================
    # FORMATAÇÃO
    # =====================================================

    @staticmethod
    def format_value(
        value,
        currency: str,
    ) -> str:
        """
        Formata um valor já na moeda de destino.

        Exemplos:
            format_value(121.37, "BRL") -> "R$ 121,37"
            format_value(22.06, "USD")  -> "US$ 22,06"
            format_value(111.66, "EUR") -> "€ 111,66"
            format_value(20.1, "TIX")   -> "Tix 20,10"
        """

        try:

            value = float(
                value
                or 0
            )

        except (
            TypeError,
            ValueError,
        ):

            value = 0.0

        currency = str(
            currency or "USD"
        ).upper()

        symbol = CURRENCY_SYMBOLS.get(
            currency,
            currency,
        )

        formatted = (
            f"{value:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

        return (
            f"{symbol} {formatted}"
        )

    @staticmethod
    def format_usd(
        value,
    ) -> str:
        return CurrencyService.format_value(
            value,
            "USD",
        )

    # =====================================================
    # VALOR INFORMATIVO DA MOEDA
    # =====================================================

    @staticmethod
    def secondary_currency(
        currency: str,
    ) -> str:
        """
        Moeda exibida como referência secundária
        no card Valor Estimado.
        """

        if currency == "USD":
            return "BRL"

        return "USD"


# =========================================================
# ATALHO DE CONVERSÃO PARA O MÓDULO
# =========================================================


def convert_usd_to_currency(
    amount_usd,
    currency: str,
) -> float:
    return CurrencyService.convert_usd(
        amount_usd,
        currency,
    )