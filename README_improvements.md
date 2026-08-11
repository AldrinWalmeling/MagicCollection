# Melhorias Implementadas

## 🎯 Objetivo

Implementar melhorias na experiência do usuário, incluindo:
- Exibição de verso das cartas (double-faced)
- Seleção de idioma do texto
- Seleção de arte alternativa
- Exportação completa com dados do Scryfall
- Migração automática do banco de dados

## 📁 Arquivos Modificados

### 1. `components/card_details_dialog.py` (NOVO)
**Diálogo de detalhes da carta com suporte a:**
- ✅ Múltiplas faces (verso)
- ✅ Múltiplas artes por face
- ✅ Seleção de idioma do texto (pt, en, es, fr, de, it, ja, ko, zhs, zht, ru)
- ✅ Exibição de texto no idioma selecionado
- ✅ Cache de imagens por face/arte
- ✅ Exibição de poder/resistência

**Principais recursos:**
- `ImageTask` modificado para aceitar `face_index` e `art_index`
- Cache de disco separado por face e arte
- `get_localized_text()` busca texto no idioma selecionado
- `update_art_selector()` lista artes disponíveis
- `update_display()` atualiza todos os campos

### 2. `collection_page.py`
**Modificações:**
- ✅ `ImageTask.__init__()` agora aceita `face_index` e `art_index`
- ✅ `ImageTask.run()` usa cache separado por face/arte
- ✅ `GridCardFrame` armazena `card_data` completo
- ✅ `GridCardFrame.set_card_data()` recebe dados completos
- ✅ `GridCardFrame.update_card_image()` carrega imagem do verso
- ✅ `CollectionPage.display_cards()` passa `card_data` completo
- ✅ `CollectionPage.add_card_from_input()` usa `ensure_card_exists()`
- ✅ `CollectionPage.update_card_quantity_in_list()` atualiza dicts
- ✅ Remoção de duplicação em `on_language_toggled` e `update_language_button`
- ✅ Atualização automática do contador de coleção

### 3. `decks_page.py`
**Modificações:**
- ✅ `DeckCardFrame` armazena `card_data` completo
- ✅ `DeckCardFrame.set_card_data()` e `update_card_image()`
- ✅ `DeckPage.add_card_from_input()` usa `ensure_card_exists()`
- ✅ Suporte a cartas de verso nos decks

### 4. `collection_export.py`
**Modificações:**
- ✅ `CollectionExporter.export()` usa tabela `cards_completa`
- ✅ Inclui `card_data`, `card_faces`, `artworks` no JSON exportado
- ✅ `_parse_card_row()` faz parse de JSON dos campos adicionais

### 5. `export_dialog.py`
**Modificações:**
- ✅ Seleção de tipo de exportação (coleção completa ou deck)
- ✅ Seleção de formato (JSON, CSV)
- ✅ Diálogo de seleção de caminho de arquivo
- ✅ Carregamento de lista de decks disponíveis

### 6. `migrate_database.py` (NOVO)
**Script de migração do banco de dados:**
- ✅ Cria tabela `cards_completa` com todos os dados do Scryfall
- ✅ Adiciona colunas faltantes (`card_data`, `card_faces`, `artworks`, `scryfall_id`)
- ✅ Backfill de cartas existentes
- ✅ Cria view `collection` para compatibilidade
- ✅ Migração automática e segura

## 🚀 Como Aplicar as Melhorias

### Passo 1: Backup
```bash
# Fazer backup do banco de dados
cp media/data/collection.db media/data/collection.db.backup
