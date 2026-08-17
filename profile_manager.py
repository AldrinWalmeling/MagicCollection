"""
PROFILE MANAGER
===============

Gerenciador central dos perfis do Magic Collection.

Responsabilidades:

- Criar e remover perfis.
- Renomear perfis.
- Controlar o perfil ativo.
- Armazenar o caminho do banco de cada perfil.
- Detectar saves antigos.
- Registrar saves antigos como perfis sem alterar seus dados.
- Criar novos bancos para novos perfis.
- Manter compatibilidade com versões antigas do projeto.
- Fornecer informações básicas sobre cada perfil.

IMPORTANTE:

Este módulo NÃO gerencia cartas, decks ou dados da coleção.

Ele apenas gerencia:

    PERFIL
        ↓
    BANCO DE DADOS DO PERFIL

A coleção continua sendo responsabilidade do database.py.
"""

from __future__ import annotations

import shutil
import sqlite3
import uuid

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


# =========================================================
# CAMINHOS
# =========================================================

BASE_DIR = Path(
    __file__
).resolve().parent


# ---------------------------------------------------------
# Diretório dos perfis
# ---------------------------------------------------------

PROFILES_DIR = (
    BASE_DIR
    / "profiles"
)

PROFILES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ---------------------------------------------------------
# Banco que controla os perfis
# ---------------------------------------------------------

PROFILES_DATABASE = (
    PROFILES_DIR
    / "profiles.db"
)


# ---------------------------------------------------------
# Backups de segurança
# ---------------------------------------------------------

BACKUPS_DIR = (
    PROFILES_DIR
    / "backups"
)

BACKUPS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# POSSÍVEIS SAVES ANTIGOS
# =========================================================

LEGACY_DATABASE_CANDIDATES = (
    BASE_DIR / "save" / "save.db",
    BASE_DIR / "save.db",
)


# =========================================================
# CONSTANTES
# =========================================================

DEFAULT_PROFILE_NAME = (
    "Minha Coleção"
)

MAX_PROFILE_NAME_LENGTH = 40


# =========================================================
# MODELO
# =========================================================

@dataclass(
    frozen=True
)
class Profile:

    id: str

    name: str

    database_path: Path

    avatar_path: Optional[Path]

    is_legacy: bool

    created_at: str

    last_opened_at: Optional[str]

    @property
    def database_exists(self) -> bool:

        return (
            self.database_path.exists()
        )


# =========================================================
# EXCEÇÕES
# =========================================================

class ProfileManagerError(
    RuntimeError
):
    """
    Erro base do sistema de perfis.
    """

    pass


class ProfileNotFoundError(
    ProfileManagerError
):
    pass


class ProfileAlreadyExistsError(
    ProfileManagerError
):
    pass


class InvalidProfileNameError(
    ProfileManagerError
):
    pass


# =========================================================
# PROFILE MANAGER
# =========================================================

class ProfileManager:
    """
    Gerencia todos os perfis do Magic Collection.

    Exemplo:

        manager = ProfileManager()

        profiles = manager.get_profiles()

        manager.create_profile(
            "Minha Coleção"
        )

        manager.set_active_profile(
            profile_id
        )
    """

    # =====================================================
    # INICIALIZAÇÃO
    # =====================================================

    def __init__(
        self,
    ):

        self.base_dir = BASE_DIR

        self.profiles_dir = PROFILES_DIR

        self.database_path = (
            PROFILES_DATABASE
        )

        self.backups_dir = (
            BACKUPS_DIR
        )

        self._initialize_database()

    # =====================================================
    # CONEXÃO
    # =====================================================

    def _get_connection(
        self,
    ) -> sqlite3.Connection:

        connection = sqlite3.connect(
            str(
                self.database_path
            )
        )

        connection.row_factory = (
            sqlite3.Row
        )

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        return connection

    # =====================================================
    # BANCO DE PERFIS
    # =====================================================

    def _initialize_database(
        self,
    ):

        connection = (
            self._get_connection()
        )

        try:

            cursor = (
                connection.cursor()
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (

                    id TEXT PRIMARY KEY,

                    name TEXT NOT NULL
                        COLLATE NOCASE,

                    database_path TEXT NOT NULL,

                    avatar_path TEXT,

                    is_legacy INTEGER
                        NOT NULL
                        DEFAULT 0,

                    created_at TEXT
                        NOT NULL,

                    last_opened_at TEXT
                )
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_profiles_name
                ON profiles(name)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_profiles_last_opened
                ON profiles(last_opened_at)
                """
            )

            connection.commit()

        finally:

            connection.close()

    # =====================================================
    # DATA / HORA
    # =====================================================

    @staticmethod
    def _now() -> str:

        return (
            datetime.now()
            .isoformat(
                timespec="seconds"
            )
        )

    # =====================================================
    # NORMALIZAR NOME
    # =====================================================

    @staticmethod
    def _normalize_profile_name(
        name: str,
    ) -> str:

        if name is None:

            raise InvalidProfileNameError(
                "O nome do perfil não pode ser vazio."
            )

        name = str(
            name
        ).strip()

        if not name:

            raise InvalidProfileNameError(
                "O nome do perfil não pode ser vazio."
            )

        if len(name) > MAX_PROFILE_NAME_LENGTH:

            raise InvalidProfileNameError(
                (
                    "O nome do perfil deve possuir "
                    f"no máximo {MAX_PROFILE_NAME_LENGTH} caracteres."
                )
            )

        return name

    # =====================================================
    # ID
    # =====================================================

    @staticmethod
    def _generate_profile_id() -> str:

        return uuid.uuid4().hex

    # =====================================================
    # SLUG
    # =====================================================

    @staticmethod
    def _safe_folder_name(
        name: str,
    ) -> str:

        invalid_characters = (
            '<>:"/\\|?*'
        )

        result = "".join(
            "_"
            if character
            in invalid_characters
            else character
            for character
            in name
        )

        result = result.strip()

        if not result:

            result = "profile"

        return result

    # =====================================================
    # DETECTAR SAVE ANTIGO
    # =====================================================

    def find_legacy_database(
        self,
    ) -> Optional[Path]:
        """
        Procura o banco antigo sem modificá-lo.

        Ordem:

        1. collection.db
        2. save/save.db
        3. save.db
        """

        for candidate in (
            LEGACY_DATABASE_CANDIDATES
        ):

            try:

                if (
                    candidate.exists()
                    and candidate.is_file()
                    and candidate.stat().st_size > 0
                ):

                    return candidate.resolve()

            except OSError:

                continue

        return None

    # =====================================================
    # EXISTE SAVE ANTIGO?
    # =====================================================

    def has_legacy_database(
        self,
    ) -> bool:

        return (
            self.find_legacy_database()
            is not None
        )

    # =====================================================
    # PERFIS
    # =====================================================

    def get_profiles(
        self,
    ) -> list[Profile]:

        connection = (
            self._get_connection()
        )

        try:

            rows = connection.execute(
                """
                SELECT
                    id,
                    name,
                    database_path,
                    avatar_path,
                    is_legacy,
                    created_at,
                    last_opened_at
                FROM profiles
                ORDER BY
                    CASE
                        WHEN last_opened_at IS NULL
                        THEN 1
                        ELSE 0
                    END,
                    last_opened_at DESC,
                    created_at ASC
                """
            ).fetchall()

        finally:

            connection.close()

        return [
            self._row_to_profile(
                row
            )
            for row in rows
        ]

    # =====================================================
    # BUSCAR PERFIL
    # =====================================================

    def get_profile(
        self,
        profile_id: str,
    ) -> Profile:

        if not profile_id:

            raise ProfileNotFoundError(
                "ID do perfil inválido."
            )

        connection = (
            self._get_connection()
        )

        try:

            row = connection.execute(
                """
                SELECT
                    id,
                    name,
                    database_path,
                    avatar_path,
                    is_legacy,
                    created_at,
                    last_opened_at
                FROM profiles
                WHERE id = ?
                """,
                (
                    profile_id,
                ),
            ).fetchone()

        finally:

            connection.close()

        if row is None:

            raise ProfileNotFoundError(
                (
                    "Perfil não encontrado: "
                    f"{profile_id}"
                )
            )

        return self._row_to_profile(
            row
        )

    # =====================================================
    # CONVERTER ROW
    # =====================================================

    def _row_to_profile(
        self,
        row: sqlite3.Row,
    ) -> Profile:

        database_path = Path(
            row["database_path"]
        )

        if not database_path.is_absolute():

            database_path = (
                self.base_dir
                / database_path
            )

        avatar_path = None

        if row["avatar_path"]:

            avatar_path = Path(
                row["avatar_path"]
            )

            if not avatar_path.is_absolute():

                avatar_path = (
                    self.base_dir
                    / avatar_path
                )

        return Profile(
            id=row["id"],
            name=row["name"],
            database_path=database_path,
            avatar_path=avatar_path,
            is_legacy=bool(
                row["is_legacy"]
            ),
            created_at=row["created_at"],
            last_opened_at=row[
                "last_opened_at"
            ],
        )

    # =====================================================
    # PERFIL ATIVO
    # =====================================================

    def get_active_profile(
        self,
    ) -> Optional[Profile]:
        """
        O perfil ativo é o último perfil aberto.

        Não criamos uma segunda tabela apenas para isso.

        O campo last_opened_at funciona como estado
        persistente do perfil ativo.
        """

        connection = (
            self._get_connection()
        )

        try:

            row = connection.execute(
                """
                SELECT
                    id,
                    name,
                    database_path,
                    avatar_path,
                    is_legacy,
                    created_at,
                    last_opened_at
                FROM profiles
                WHERE last_opened_at IS NOT NULL
                ORDER BY
                    last_opened_at DESC
                LIMIT 1
                """
            ).fetchone()

        finally:

            connection.close()

        if row is None:

            return None

        return self._row_to_profile(
            row
        )

    # =====================================================
    # BANCO DO PERFIL ATIVO
    # =====================================================

    def get_active_database_path(
        self,
    ) -> Optional[Path]:
        """
        Retorna o banco de dados pertencente ao
        perfil atualmente ativo.

        Se não existir perfil ativo, retorna None.
        """

        profile = (
            self.get_active_profile()
        )

        if profile is None:
            return None

        return (
            profile.database_path
        )


    # =====================================================
    # EXISTE PERFIL?
    # =====================================================

    def has_profiles(
        self,
    ) -> bool:

        connection = (
            self._get_connection()
        )

        try:

            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM profiles
                """
            ).fetchone()

        finally:

            connection.close()

        return (
            row["total"] > 0
        )

    # =====================================================
    # QUANTIDADE
    # =====================================================

    def profile_count(
        self,
    ) -> int:

        connection = (
            self._get_connection()
        )

        try:

            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM profiles
                """
            ).fetchone()

        finally:

            connection.close()

        return int(
            row["total"]
        )

    # =====================================================
    # CRIAR PERFIL
    # =====================================================

    def create_profile(
        self,
        name: str,
        avatar_path: Optional[
            str | Path
        ] = None,
    ) -> Profile:
        """
        Cria um novo perfil.

        O banco do perfil é criado vazio.

        A criação das tabelas de cards/decks continuará
        sendo responsabilidade do database.py.
        """

        name = (
            self._normalize_profile_name(
                name
            )
        )

        if self._profile_name_exists(
            name
        ):

            raise ProfileAlreadyExistsError(
                (
                    "Já existe um perfil "
                    f"chamado '{name}'."
                )
            )

        profile_id = (
            self._generate_profile_id()
        )

        folder_name = (
            self._safe_folder_name(
                name
            )
        )

        profile_directory = (
            self.profiles_dir
            / f"{folder_name}_{profile_id[:8]}"
        )

        profile_directory.mkdir(
            parents=True,
            exist_ok=False,
        )

        database_path = (
            profile_directory
            / "save.db"
        )

        # Criar o arquivo SQLite.
        connection = sqlite3.connect(
            str(
                database_path
            )
        )

        connection.close()

        normalized_avatar = None

        if avatar_path:

            avatar = Path(
                avatar_path
            ).expanduser()

            if avatar.exists():

                normalized_avatar = (
                    avatar.resolve()
                )

        created_at = (
            self._now()
        )

        connection = (
            self._get_connection()
        )

        try:

            connection.execute(
                """
                INSERT INTO profiles (
                    id,
                    name,
                    database_path,
                    avatar_path,
                    is_legacy,
                    created_at,
                    last_opened_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    name,
                    str(
                        database_path
                        .resolve()
                    ),
                    (
                        str(
                            normalized_avatar
                        )
                        if normalized_avatar
                        else None
                    ),
                    0,
                    created_at,
                    None,
                ),
            )

            connection.commit()

        except Exception:

            connection.rollback()

            try:

                if database_path.exists():

                    database_path.unlink()

                if (
                    profile_directory.exists()
                    and not any(
                        profile_directory.iterdir()
                    )
                ):

                    profile_directory.rmdir()

            except OSError:

                pass

            raise

        finally:

            connection.close()

        return self.get_profile(
            profile_id
        )

    # =====================================================
    # REGISTRAR SAVE ANTIGO
    # =====================================================

    # =====================================================
    # IMPORTAR SAVE ANTIGO COMO NOVO PERFIL
    # =====================================================

    def register_legacy_profile(
        self,
        name: str,
        database_path: Optional[
            str | Path
        ] = None,
        avatar_path: Optional[
            str | Path
        ] = None,
    ) -> Profile:
        """
        Importa o save antigo para um novo perfil.

        IMPORTANTE:

        - O save antigo NÃO é alterado.
        - O save antigo NÃO é movido.
        - O save antigo NÃO é excluído.
        - O novo perfil recebe uma cópia independente.
        """

        name = (
            self._normalize_profile_name(
                name
            )
        )

        if self._profile_name_exists(
            name
        ):
            raise ProfileAlreadyExistsError(
                (
                    "Já existe um perfil "
                    f"chamado '{name}'."
                )
            )

        # -------------------------------------------------
        # Localizar save antigo
        # -------------------------------------------------

        if database_path is None:
            database_path = (
                self.find_legacy_database()
            )

        if database_path is None:
            raise ProfileManagerError(
                "Nenhum save antigo foi encontrado."
            )

        source = (
            Path(database_path)
            .expanduser()
            .resolve()
        )

        if not source.exists():
            raise ProfileManagerError(
                (
                    "O save antigo não existe:\n"
                    f"{source}"
                )
            )

        if not source.is_file():
            raise ProfileManagerError(
                (
                    "O caminho do save antigo "
                    "não é um arquivo:\n"
                    f"{source}"
                )
            )

        # -------------------------------------------------
        # ID / diretório
        # -------------------------------------------------

        profile_id = (
            self._generate_profile_id()
        )

        folder_name = (
            self._safe_folder_name(
                name
            )
        )

        profile_directory = (
            self.profiles_dir
            / f"{folder_name}_{profile_id[:8]}"
        )

        profile_directory.mkdir(
            parents=True,
            exist_ok=False,
        )

        database_destination = (
            profile_directory
            / "save.db"
        )

        try:

            # =================================================
            # COPIAR BANCO COM SQLITE BACKUP
            # =================================================
            #
            # Preferimos o mecanismo nativo do SQLite
            # em vez de simplesmente copiar bytes.
            #
            # Isso é mais seguro caso o banco esteja aberto
            # ou possua estruturas auxiliares do SQLite.
            #

            source_connection = None
            destination_connection = None

            try:

                source_connection = (
                    sqlite3.connect(
                        str(source)
                    )
                )

                destination_connection = (
                    sqlite3.connect(
                        str(
                            database_destination
                        )
                    )
                )

                source_connection.backup(
                    destination_connection
                )

                destination_connection.commit()

            finally:

                if source_connection is not None:
                    source_connection.close()

                if destination_connection is not None:
                    destination_connection.close()

            # =================================================
            # VERIFICAR CÓPIA
            # =================================================

            check_connection = (
                sqlite3.connect(
                    str(
                        database_destination
                    )
                )
            )

            try:

                result = (
                    check_connection
                    .execute(
                        "PRAGMA integrity_check"
                    )
                    .fetchone()
                )

            finally:

                check_connection.close()

            if (
                not result
                or result[0] != "ok"
            ):
                raise ProfileManagerError(
                    (
                        "A cópia do save antigo "
                        "não passou na verificação "
                        "de integridade."
                    )
                )

            # -------------------------------------------------
            # Avatar
            # -------------------------------------------------

            normalized_avatar = None

            if avatar_path:

                avatar = (
                    Path(
                        avatar_path
                    )
                    .expanduser()
                )

                if avatar.exists():

                    normalized_avatar = (
                        avatar.resolve()
                    )

            # -------------------------------------------------
            # Registrar perfil
            # -------------------------------------------------

            created_at = (
                self._now()
            )

            connection = (
                self._get_connection()
            )

            try:

                connection.execute(
                    """
                    INSERT INTO profiles (
                        id,
                        name,
                        database_path,
                        avatar_path,
                        is_legacy,
                        created_at,
                        last_opened_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        profile_id,
                        name,
                        str(
                            database_destination
                            .resolve()
                        ),
                        (
                            str(
                                normalized_avatar
                            )
                            if normalized_avatar
                            else None
                        ),
                        # IMPORTANTE:
                        #
                        # Depois da cópia ele é um
                        # perfil normal e independente.
                        #
                        0,
                        created_at,
                        None,
                    ),
                )

                connection.commit()

            finally:

                connection.close()

            return self.get_profile(
                profile_id
            )

        except Exception:

            # -------------------------------------------------
            # Rollback físico
            # -------------------------------------------------

            try:

                if (
                    database_destination.exists()
                ):
                    database_destination.unlink()

                if (
                    profile_directory.exists()
                    and not any(
                        profile_directory.iterdir()
                    )
                ):
                    profile_directory.rmdir()

            except OSError:
                pass

            raise
    # =====================================================
    # ATIVAR PERFIL
    # =====================================================

    def set_active_profile(
        self,
        profile_id: str,
    ) -> Profile:
        """
        Define o perfil ativo.

        Apenas um perfil permanece marcado como último aberto.
        """

        profile = self.get_profile(
            profile_id
        )

        timestamp = (
            self._now()
        )

        connection = (
            self._get_connection()
        )

        try:

            # Primeiro limpa o estado anterior.
            connection.execute(
                """
                UPDATE profiles
                SET last_opened_at = NULL
                """
            )

            # Depois ativa o novo.
            connection.execute(
                """
                UPDATE profiles
                SET last_opened_at = ?
                WHERE id = ?
                """,
                (
                    timestamp,
                    profile_id,
                ),
            )

            connection.commit()

        finally:

            connection.close()

        return self.get_profile(
            profile.id
        )

    # =====================================================
    # RENOMEAR
    # =====================================================

    def rename_profile(
        self,
        profile_id: str,
        new_name: str,
    ) -> Profile:

        new_name = (
            self._normalize_profile_name(
                new_name
            )
        )

        profile = self.get_profile(
            profile_id
        )

        if (
            profile.name.casefold()
            != new_name.casefold()
            and self._profile_name_exists(
                new_name
            )
        ):

            raise ProfileAlreadyExistsError(
                (
                    "Já existe um perfil "
                    f"chamado '{new_name}'."
                )
            )

        connection = (
            self._get_connection()
        )

        try:

            connection.execute(
                """
                UPDATE profiles
                SET name = ?
                WHERE id = ?
                """,
                (
                    new_name,
                    profile_id,
                ),
            )

            connection.commit()

        finally:

            connection.close()

        return self.get_profile(
            profile_id
        )

    # =====================================================
    # AVATAR
    # =====================================================

    def set_avatar(
        self,
        profile_id: str,
        avatar_path: Optional[
            str | Path
        ],
    ) -> Profile:

        self.get_profile(
            profile_id
        )

        normalized = None

        if avatar_path:

            path = Path(
                avatar_path
            ).expanduser()

            if not path.exists():

                raise ProfileManagerError(
                    (
                        "A imagem do avatar "
                        "não existe."
                    )
                )

            if not path.is_file():

                raise ProfileManagerError(
                    (
                        "O avatar informado "
                        "não é um arquivo."
                    )
                )

            normalized = (
                path.resolve()
            )

        connection = (
            self._get_connection()
        )

        try:

            connection.execute(
                """
                UPDATE profiles
                SET avatar_path = ?
                WHERE id = ?
                """,
                (
                    (
                        str(normalized)
                        if normalized
                        else None
                    ),
                    profile_id,
                ),
            )

            connection.commit()

        finally:

            connection.close()

        return self.get_profile(
            profile_id
        )

    # =====================================================
    # REMOVER PERFIL
    # =====================================================

    def delete_profile(
        self,
        profile_id: str,
        delete_database: bool = False,
    ):
        """
        Remove o registro do perfil.

        Por segurança, o banco NÃO é removido por padrão.

        Para apagar fisicamente um banco, é necessário:

            delete_database=True

        Mesmo assim, saves legados nunca são apagados
        por este método.
        """

        profile = self.get_profile(
            profile_id
        )

        profiles = self.get_profiles()

        if len(profiles) <= 1:

            raise ProfileManagerError(
                (
                    "Não é possível remover o "
                    "último perfil."
                )
            )

        connection = (
            self._get_connection()
        )

        try:

            connection.execute(
                """
                DELETE FROM profiles
                WHERE id = ?
                """,
                (
                    profile_id,
                ),
            )

            connection.commit()

        finally:

            connection.close()

        # -------------------------------------------------
        # Banco de perfil novo
        # -------------------------------------------------

        if (
            delete_database
            and not profile.is_legacy
        ):

            self._safe_delete_database(
                profile.database_path
            )

        # -------------------------------------------------
        # Se era o perfil ativo,
        # escolhemos outro.
        # -------------------------------------------------

        if (
            profile.last_opened_at
            is not None
        ):

            remaining = (
                self.get_profiles()
            )

            if remaining:

                self.set_active_profile(
                    remaining[0].id
                )

    # =====================================================
    # BACKUP
    # =====================================================

    def backup_database(
        self,
        profile_id: str,
    ) -> Optional[Path]:
        """
        Cria uma cópia de segurança do banco do perfil.

        Nunca altera o banco original.
        """

        profile = self.get_profile(
            profile_id
        )

        source = (
            profile.database_path
        )

        if not source.exists():

            return None

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        backup_name = (
            f"{profile.id}_{timestamp}.db"
        )

        destination = (
            self.backups_dir
            / backup_name
        )

        shutil.copy2(
            source,
            destination,
        )

        return destination

    # =====================================================
    # VERIFICAR INTEGRIDADE
    # =====================================================

    def check_database(
        self,
        profile_id: str,
    ) -> bool:

        profile = self.get_profile(
            profile_id
        )

        path = (
            profile.database_path
        )

        if not path.exists():

            return False

        try:

            connection = sqlite3.connect(
                str(path)
            )

            result = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()

            connection.close()

            return (
                bool(result)
                and result[0] == "ok"
            )

        except sqlite3.Error:

            return False

    # =====================================================
    # STATUS INICIAL
    # =====================================================

    def get_startup_state(
        self,
    ) -> dict:
        """
        Retorna o estado necessário para decidir
        qual tela deve aparecer na inicialização.

        Possíveis estados:

            no_profiles
            has_profiles
            legacy_available
        """

        profiles = (
            self.get_profiles()
        )

        legacy_database = (
            self.find_legacy_database()
        )

        if not profiles:

            if legacy_database:

                return {
                    "state": "legacy_available",
                    "profiles": [],
                    "legacy_database": (
                        legacy_database
                    ),
                }

            return {
                "state": "no_profiles",
                "profiles": [],
                "legacy_database": None,
            }

        active = (
            self.get_active_profile()
        )

        return {
            "state": "has_profiles",
            "profiles": profiles,
            "active_profile": active,
            "legacy_database": (
                legacy_database
            ),
        }

    # =====================================================
    # PERFIL POR NOME
    # =====================================================

    def find_by_name(
        self,
        name: str,
    ) -> Optional[Profile]:

        name = str(
            name
        ).strip()

        if not name:

            return None

        connection = (
            self._get_connection()
        )

        try:

            row = connection.execute(
                """
                SELECT
                    id,
                    name,
                    database_path,
                    avatar_path,
                    is_legacy,
                    created_at,
                    last_opened_at
                FROM profiles
                WHERE name = ?
                COLLATE NOCASE
                LIMIT 1
                """,
                (
                    name,
                ),
            ).fetchone()

        finally:

            connection.close()

        if row is None:

            return None

        return self._row_to_profile(
            row
        )

    # =====================================================
    # NOME EXISTE
    # =====================================================

    def _profile_name_exists(
        self,
        name: str,
    ) -> bool:

        return (
            self.find_by_name(
                name
            )
            is not None
        )

    # =====================================================
    # DELETAR BANCO COM SEGURANÇA
    # =====================================================

    @staticmethod
    def _safe_delete_database(
        database_path: Path,
    ):

        try:

            if (
                database_path.exists()
                and database_path.is_file()
            ):

                database_path.unlink()

        except OSError as error:

            raise ProfileManagerError(
                (
                    "Não foi possível excluir "
                    f"o banco:\n{database_path}\n\n"
                    f"Erro: {error}"
                )
            )

    # =====================================================
    # DEBUG
    # =====================================================

    def debug_print(
        self,
    ):

        print()
        print(
            "========================================"
        )
        print(
            " PROFILE MANAGER"
        )
        print(
            "========================================"
        )

        print(
            "Profiles DB:"
        )

        print(
            f"  {self.database_path}"
        )

        print()

        print(
            "Perfis:"
        )

        profiles = (
            self.get_profiles()
        )

        if not profiles:

            print(
                "  Nenhum perfil."
            )

        else:

            for profile in profiles:

                active = (
                    " [ATIVO]"
                    if profile.last_opened_at
                    else ""
                )

                legacy = (
                    " [LEGACY]"
                    if profile.is_legacy
                    else ""
                )

                print(
                    f"  • {profile.name}"
                    f"{active}"
                    f"{legacy}"
                )

                print(
                    f"    ID: {profile.id}"
                )

                print(
                    "    DB:"
                    f" {profile.database_path}"
                )

        print()
        print(
            "Save antigo:"
        )

        legacy = (
            self.find_legacy_database()
        )

        if legacy:

            print(
                f"  {legacy}"
            )

        else:

            print(
                "  Nenhum encontrado."
            )

        print(
            "========================================"
        )
        print()


# =========================================================
# INSTÂNCIA GLOBAL
# =========================================================

profile_manager = ProfileManager()