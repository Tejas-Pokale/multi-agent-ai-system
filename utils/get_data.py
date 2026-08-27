# app/get_data.py

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any

import pandas as pd


# =============================================================================
# Configuration
# =============================================================================

# Expected project structure:
#
# project/
# ├── data/
# │   ├── accounts.json
# │   └── tickets.json
# │
# └── app/
#     └── get_data.py
#
# If your data directory is somewhere else, update DATA_DIR.

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ACCOUNTS_JSON = DATA_DIR / "accounts.json"
TICKETS_JSON = DATA_DIR / "tickets.json"


# Default reference date.
#
# The Streamlit application can provide an explicit analysis date.
# When no date is supplied, today's date is used.
REFERENCE_DATE = date.today()


# =============================================================================
# JSON Loading
# =============================================================================

def _load_json(
    file_path: Path,
) -> list[dict[str, Any]]:
    """
    Load a JSON file containing a list of objects.

    This function is called only once for each dataset when
    AccountDataStore is initialized.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"Dataset file not found: {file_path}\n"
            "Please update DATA_DIR in get_data.py."
        )

    try:
        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON file: {file_path}"
        ) from exc

    if not isinstance(data, list):
        raise ValueError(
            f"Expected {file_path.name} to contain a JSON list."
        )

    if not all(
        isinstance(record, dict)
        for record in data
    ):
        raise ValueError(
            f"Every record in {file_path.name} "
            "must be a JSON object."
        )

    return data


# =============================================================================
# Data Store
# =============================================================================

class AccountDataStore:
    """
    In-memory data store for accounts and tickets.

    The JSON datasets are loaded exactly once when this object is created.

    After initialization:

        accounts.json
              ↓
        accounts DataFrame
              ↓
        account lookup

        tickets.json
              ↓
        tickets DataFrame
              ↓
        normalized timestamps

    Subsequent calls do not reload either JSON file.
    """

    def __init__(
        self,
        accounts_path: Path = ACCOUNTS_JSON,
        tickets_path: Path = TICKETS_JSON,
        reference_date=REFERENCE_DATE,
    ) -> None:

        self.accounts_path = Path(
            accounts_path
        )

        self.tickets_path = Path(
            tickets_path
        )

        self.reference_date = (
            self._normalize_reference_date(
                reference_date
            )
        )

        # ---------------------------------------------------------------------
        # Load JSON exactly once.
        # ---------------------------------------------------------------------

        accounts = _load_json(
            self.accounts_path
        )

        tickets = _load_json(
            self.tickets_path
        )

        # ---------------------------------------------------------------------
        # Convert JSON to DataFrames exactly once.
        # ---------------------------------------------------------------------

        self.accounts_df = pd.DataFrame(
            accounts
        )

        self.tickets_df = pd.DataFrame(
            tickets
        )

        # ---------------------------------------------------------------------
        # Prepare datasets.
        # ---------------------------------------------------------------------

        self._prepare_accounts()
        self._prepare_tickets()

        # ---------------------------------------------------------------------
        # Account lookup.
        #
        # This prevents scanning the complete DataFrame for every lookup.
        # ---------------------------------------------------------------------

        self._account_lookup = {
            row["account_id"]: row.to_dict()
            for _, row in self.accounts_df.iterrows()
        }

    # =========================================================================
    # Date handling
    # =========================================================================

    @staticmethod
    def _normalize_reference_date(
        reference_date=None,
    ) -> pd.Timestamp:
        """
        Convert an analysis date into a UTC timestamp representing the
        END of that calendar day.

        Example:

            2026-08-27

        becomes approximately:

            2026-08-27 23:59:59.999999 UTC

        This allows the selected analysis date to be inclusive.
        """

        if reference_date is None:
            timestamp = pd.Timestamp.now(
                tz="UTC"
            )

        else:
            timestamp = pd.Timestamp(
                reference_date
            )

            if timestamp.tzinfo is None:
                timestamp = timestamp.tz_localize(
                    "UTC"
                )
            else:
                timestamp = timestamp.tz_convert(
                    "UTC"
                )

        return (
            timestamp.normalize()
            + pd.Timedelta(days=1)
            - pd.Timedelta(microseconds=1)
        )

    # =========================================================================
    # Data preparation
    # =========================================================================

    def _prepare_accounts(self) -> None:
        """
        Validate the accounts dataset.
        """

        if self.accounts_df.empty:
            raise ValueError(
                "Accounts dataset is empty."
            )

        required_columns = {
            "account_id",
            "company",
            "health_status",
            "usage_trend",
        }

        missing_columns = (
            required_columns
            - set(self.accounts_df.columns)
        )

        if missing_columns:
            raise ValueError(
                "Accounts dataset is missing required "
                f"columns: {sorted(missing_columns)}"
            )

        duplicate_ids = (
            self.accounts_df["account_id"]
            .duplicated()
        )

        if duplicate_ids.any():

            duplicates = (
                self.accounts_df.loc[
                    duplicate_ids,
                    "account_id",
                ]
                .tolist()
            )

            raise ValueError(
                "Duplicate account IDs found: "
                f"{duplicates}"
            )

    def _prepare_tickets(self) -> None:
        """
        Validate and normalize the tickets dataset.

        Ticket timestamps are converted once during initialization.
        """

        if self.tickets_df.empty:
            return

        required_columns = {
            "ticket_id",
            "account_id",
            "created_at",
            "subject",
            "body",
            "urgency",
            "status",
        }

        missing_columns = (
            required_columns
            - set(self.tickets_df.columns)
        )

        if missing_columns:
            raise ValueError(
                "Tickets dataset is missing required "
                f"columns: {sorted(missing_columns)}"
            )

        self.tickets_df["created_at"] = (
            pd.to_datetime(
                self.tickets_df["created_at"],
                utc=True,
                errors="coerce",
            )
        )

        # Invalid timestamps cannot be used for filtering.
        self.tickets_df = (
            self.tickets_df
            .dropna(
                subset=["created_at"]
            )
            .copy()
        )

        # Deterministic ordering.
        self.tickets_df = (
            self.tickets_df
            .sort_values(
                by=[
                    "created_at",
                    "ticket_id",
                ],
                ascending=[
                    False,
                    True,
                ],
                kind="mergesort",
            )
            .reset_index(
                drop=True
            )
        )

    # =========================================================================
    # Account retrieval
    # =========================================================================

    def get_account_data(
        self,
        account_id: str,
    ) -> dict[str, Any]:
        """
        Return the complete account record for an account ID.
        """

        account_id = self._validate_account_id(
            account_id
        )

        account = self._account_lookup.get(
            account_id
        )

        if account is None:
            raise KeyError(
                f"Account '{account_id}' was not found."
            )

        return account.copy()

    # =========================================================================
    # Ticket retrieval
    # =========================================================================

    def get_tickets(
        self,
        account_id: str,
        days: int = 90,
        reference_date=None,
    ) -> pd.DataFrame:
        """
        Return tickets for an account within the requested analysis window.

        The window is:

            reference_date - days
            through
            reference_date

        The reference date is inclusive.

        Example:

            reference_date = 2026-08-27
            days = 90

        analyzes the 90-day window ending on 2026-08-27.
        """

        account_id = self._validate_account_id(
            account_id
        )

        if not isinstance(days, int):
            raise ValueError(
                "days must be an integer."
            )

        if days <= 0:
            raise ValueError(
                "days must be a positive integer."
            )

        if reference_date is None:
            reference_date = (
                self.reference_date
            )
        else:
            reference_date = (
                self._normalize_reference_date(
                    reference_date
                )
            )

        start_date = (
            reference_date
            - pd.Timedelta(days=days)
        )

        # ---------------------------------------------------------------------
        # Filter account first.
        # ---------------------------------------------------------------------

        account_tickets = (
            self.tickets_df[
                self.tickets_df["account_id"]
                == account_id
            ]
            .copy()
        )

        if account_tickets.empty:
            return account_tickets.reset_index(
                drop=True
            )

        # ---------------------------------------------------------------------
        # created_at has already been normalized during initialization.
        # Do NOT call pd.to_datetime() again here.
        # ---------------------------------------------------------------------

        filtered_tickets = (
            account_tickets[
                (
                    account_tickets["created_at"]
                    > start_date
                )
                & (
                    account_tickets["created_at"]
                    <= reference_date
                )
            ]
            .copy()
        )

        # Deterministic ordering.
        filtered_tickets = (
            filtered_tickets
            .sort_values(
                by=[
                    "created_at",
                    "ticket_id",
                ],
                ascending=[
                    False,
                    True,
                ],
                kind="mergesort",
            )
            .reset_index(
                drop=True
            )
        )

        return (
            filtered_tickets\
            .astype({
                'created_at': str,
                'updated_at': str
            })
        )

    # =========================================================================
    # Deterministic account metrics
    # =========================================================================

    def get_account_metrics(
        self,
        account_id: str,
        tickets: pd.DataFrame | None = None,
    ) -> dict[str, Any]:
        """
        Calculate deterministic account-health metrics.

        Arithmetic and counting are performed in Python rather than by
        the LLM.
        """

        account = self.get_account_data(
            account_id=account_id
        )

        if tickets is None:
            tickets = self.get_tickets(
                account_id=account_id,
                days=90,
            )

        licensed_seats = (
            account.get(
                "seats_licensed",
                0,
            )
            or 0
        )

        active_seats = (
            account.get(
                "seats_active",
                0,
            )
            or 0
        )

        # ---------------------------------------------------------------------
        # Seat utilization
        # ---------------------------------------------------------------------

        if licensed_seats > 0:

            seat_utilization = round(
                (
                    active_seats
                    / licensed_seats
                )
                * 100,
                2,
            )

        else:
            seat_utilization = None

        # ---------------------------------------------------------------------
        # Ticket metrics
        # ---------------------------------------------------------------------

        if tickets.empty:

            tickets_last_90d = 0
            open_tickets_last_90d = 0
            p1_tickets_last_90d = 0
            p2_tickets_last_90d = 0
            average_ticket_satisfaction = None

        else:

            tickets_last_90d = len(
                tickets
            )

            open_statuses = {
                "Open",
                "In Progress",
                "Pending Customer",
            }

            open_tickets_last_90d = int(
                tickets["status"]
                .isin(open_statuses)
                .sum()
            )

            p1_tickets_last_90d = int(
                (
                    tickets["urgency"]
                    == "P1"
                ).sum()
            )

            p2_tickets_last_90d = int(
                (
                    tickets["urgency"]
                    == "P2"
                ).sum()
            )

            if (
                "satisfaction_score"
                in tickets.columns
            ):

                satisfaction = pd.to_numeric(
                    tickets[
                        "satisfaction_score"
                    ],
                    errors="ignore",
                )

                average_value = (
                    satisfaction.mean()
                )

                average_ticket_satisfaction = (
                    round(
                        float(average_value),
                        2,
                    )
                    if pd.notna(
                        average_value
                    )
                    else None
                )

            else:

                average_ticket_satisfaction = None

        return {
            "seat_utilization_percent": (
                seat_utilization
            ),
            "licensed_seats": int(
                licensed_seats
            ),
            "active_seats": int(
                active_seats
            ),
            "tickets_last_90d": int(
                tickets_last_90d
            ),
            "open_tickets_last_90d": int(
                open_tickets_last_90d
            ),
            "p1_tickets_last_90d": int(
                p1_tickets_last_90d
            ),
            "p2_tickets_last_90d": int(
                p2_tickets_last_90d
            ),
            "average_ticket_satisfaction": (
                average_ticket_satisfaction
            ),
        }

    # =========================================================================
    # Combined context for LangChain
    # =========================================================================

    def get_account_context(
        self,
        account_id: str,
        days: int = 90,
        reference_date=None,
    ) -> dict[str, Any]:
        """
        Return everything required by the LangChain summarisation pipeline.

        Returns:

            {
                "account": {...},
                "tickets": [...],
                "metrics": {...}
            }

        This method intentionally uses get_account_metrics(), which is the
        actual metric method defined in this class.
        """

        account = self.get_account_data(
            account_id=account_id
        )

        tickets_df = self.get_tickets(
            account_id=account_id,
            days=days,
            reference_date=reference_date,
        )

        metrics = self.get_account_metrics(
            account_id=account_id,
            tickets=tickets_df,
        )

        ticket_records = tickets_df.to_dict(orient="records")

        # for ticket in ticket_records:
        #     if pd.notna(ticket.get("created_at")):
        #         ticket["created_at"] = ticket["created_at"].isoformat()

        #     if pd.notna(ticket.get("updated_at")):
        #         ticket["updated_at"] = ticket["updated_at"].isoformat()

        return {
            "account": account,
            "tickets": ticket_records,
            "metrics": metrics,
        }

    # =========================================================================
    # Utility functions
    # =========================================================================

    def account_exists(
        self,
        account_id: str,
    ) -> bool:
        """
        Check whether an account exists without raising an exception.
        """

        if (
            not isinstance(
                account_id,
                str,
            )
            or not account_id.strip()
        ):
            return False

        return (
            account_id.strip()
            in self._account_lookup
        )

    def get_available_account_ids(
        self,
    ) -> list[str]:
        """
        Return all available account IDs in deterministic order.
        """

        return sorted(
            self._account_lookup.keys()
        )

    def get_dataset_stats(
        self,
    ) -> dict[str, int]:
        """
        Return basic dataset statistics.
        """

        return {
            "accounts": len(
                self.accounts_df
            ),
            "tickets": len(
                self.tickets_df
            ),
        }

    # =========================================================================
    # Validation helpers
    # =========================================================================

    @staticmethod
    def _validate_account_id(
        account_id: str,
    ) -> str:
        """
        Validate and normalize account ID input.
        """

        if not isinstance(
            account_id,
            str,
        ):
            raise ValueError(
                "account_id must be a string."
            )

        account_id = account_id.strip()

        if not account_id:
            raise ValueError(
                "account_id cannot be empty."
            )

        return account_id


# =============================================================================
# Single shared data store
# =============================================================================

# IMPORTANT:
#
# The JSON files are loaded exactly once here.
#
# summary.py and app.py should import the convenience functions below rather
# than creating another AccountDataStore.
#
# Therefore:
#
#     accounts.json -> loaded once
#     tickets.json  -> loaded once
#
# Subsequent account searches reuse the in-memory data.

data_store = AccountDataStore()


# =============================================================================
# Convenience functions
# =============================================================================

def get_account_data(
    account_id: str,
) -> dict[str, Any]:
    """
    Get account information using the shared data store.
    """

    return data_store.get_account_data(
        account_id=account_id
    )


def get_tickets(
    account_id: str,
    days: int = 90,
    reference_date=None,
) -> pd.DataFrame:
    """
    Get account tickets using the shared data store.
    """

    return data_store.get_tickets(
        account_id=account_id,
        days=days,
        reference_date=reference_date,
    )


def get_account_metrics(
    account_id: str,
    tickets: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """
    Get deterministic account metrics.
    """

    return data_store.get_account_metrics(
        account_id=account_id,
        tickets=tickets,
    )


def get_account_context(
    account_id: str,
    days: int = 90,
    reference_date=None,
) -> dict[str, Any]:
    """
    Get the complete context required by summary.py.

    This is the primary data function consumed by the LLM pipeline.
    """

    return data_store.get_account_context(
        account_id=account_id,
        days=days,
        reference_date=reference_date,
    )


def account_exists(
    account_id: str,
) -> bool:
    """
    Check whether an account exists.
    """

    return data_store.account_exists(
        account_id=account_id
    )


def get_available_account_ids() -> list[str]:
    """
    Return all available account IDs.
    """

    return data_store.get_available_account_ids()


# =============================================================================
# Local test
# =============================================================================

if __name__ == "__main__":

    DEMO_ACCOUNT_ID = "ACC-3336"

    print(
        "\nDataset statistics"
    )
    print(
        "------------------"
    )

    print(
        data_store.get_dataset_stats()
    )

    print(
        "\nAccount"
    )
    print(
        "-------"
    )

    try:

        account = get_account_data(
            account_id=DEMO_ACCOUNT_ID
        )

        print(account)

    except (
        ValueError,
        KeyError,
    ) as exc:

        print(
            f"ERROR: {exc}"
        )

    print(
        "\n90-day tickets"
    )
    print(
        "--------------"
    )

    try:

        tickets = get_tickets(
            account_id=DEMO_ACCOUNT_ID,
            days=90,
            reference_date=date(2026, 5, 27)
        )

        print(
            f"Tickets found: {len(tickets)}"
        )

        if not tickets.empty:

            columns_to_display = [
                "ticket_id",
                "subject",
                "urgency",
                "status",
                "created_at",
            ]

            available_columns = [
                column
                for column in columns_to_display
                if column in tickets.columns
            ]

            print(
                tickets[
                    available_columns
                ].to_string(
                    index=False
                )
            )

    except (
        ValueError,
        KeyError,
    ) as exc:

        print(
            f"ERROR: {exc}"
        )

    print(
        "\nMetrics"
    )
    print(
        "-------"
    )

    try:

        metrics = get_account_metrics(
            account_id=DEMO_ACCOUNT_ID,
            tickets=tickets,
        )

        print(metrics)

    except (
        ValueError,
        KeyError,
    ) as exc:

        print(
            f"ERROR: {exc}"
        )