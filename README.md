**English** | [Русский](README.ru.md)

# Fallout 3 GOTY — Vault-Tec Interactive 3D Knowledge Graph

An interactive bilingual (**RU / EN**) web application for exploring the complete world of **Fallout 3: Game of the Year Edition** — its characters, locations, quests, story events, items, and world objects — built directly from all **6 ESM modules** (Base Game + all 5 DLCs).

## Key Features

### 1. Interactive 3D Graph
- **Two 3D Visualization Modes**:
  - **3D Galaxy** — stratified 3D knowledge-graph constellation.
  - **3D Map** — tactical 3D world layout preserving Wasteland spatial coordinates (`mapX`, `mapY`, `mapZ`).
- **Three Detail Tiers**:
  - **Overview (Atlas)** — **413** key hubs and landmarks.
  - **Story Core** — **1,954** main storyline and quest-connected nodes.
  - **Full World** — all **4,239** entities across Fallout 3 GOTY.
- **Filtering & Navigation**:
  - Filter by **6 entity categories**, **6 game modules (Base + 5 DLCs)**, and **13 relationship types** (plus toggleable background loot & container links).
  - **1-hop / 2-hop 3D Ego-Network Isolation** — double-click any node or use the inspector to isolate its local neighborhood in 3D space.
  - **Shortest Path Finder (`A → B`)** — discover how any two entities in the Wasteland are connected.
  - **Quick-Jump Landmarks** and live instant search (`/`).
  - **Pip-Boy Icon Atlas** — **377** game icons extracted from BSA/DDS archives and packed into a WebGL texture atlas.
- **Controls**: `LMB` orbit · `RMB` pan · `Wheel` zoom · `WASD` / `QE` fly · `/` search · `R` center camera · `Double-click` 3D focus.

### 2. Quest Walkthroughs
- Complete coverage of all **81 curated quests** across the base game and all expansions:
  - Main Storyline (**16**), Side Quests (**19**), Freeform & Unmarked Quests (**17**), Operation: Anchorage (**4**), The Pitt (**4**), Broken Steel (**6**), Point Lookout (**12**), and Mothership Zeta (**3**).
- Interactive checklist to track completed quests and individual walkthrough steps.
- Detailed step-by-step guides featuring **skill checks**, **tips**, **moral / alternative branches** (Good, Evil, Neutral, Alternative), **prerequisites**, **key rewards**, and **missable warnings**.
- Official **ESM Pip-Boy Objectives (`QOBJ`)** and **Quest Stage Logs (`INDX / CNAM`)** with completion/failure markers.
- One-click navigation from any quest or linked entity directly to its node on the 3D graph.

### 3. Entity Encyclopedia (Catalog)
- Full-text search across Russian and English names, roles, descriptions, `EditorID`, and `FormID`.
- Filter by category, expansion module (GOTY), and entity subtype (NPC, creature, weapon, armor, terminal, door, perk, etc.), sorted by connection count or alphabetically.
- Rich entity inspection cards:
  - **Characters**: race, level, HP, sex, essential/unique flags, behavior, **S.P.E.C.I.A.L.** stats, factions, merchant/companion services, key inventory, and dialogue quotes.
  - **Items**: weapon class, damage, DR, ammo, clip size, fire rate, V.A.T.S. AP cost, crit damage, spread, item HP, value, weight, effects, unlocked doors/safes, and note/holotape text.
  - **Locations & Objects**: worldspace, map marker type, lock difficulty, terminal entries, and linked quests/NPCs.

### 4. World Analytics
- Summary cards and visual breakdowns of entities by category, expansion module, and all **13 relationship types**.
- Ranked list of top hub entities by connection degree with one-click jump to the 3D graph.

### 5. Bilingual Interface & Dataset (`RU` / `EN`)
- Instant language switcher (`RU | EN`) in the header, persisted in `localStorage` and configurable via `?lang=ru` or `?lang=en` URL query parameters.
- Dynamically loads localized encyclopedia entries (`details.json` / `details.en.json`) and quest walkthroughs (`walkthroughs.json` / `walkthroughs.en.json`).

## Dataset Statistics

| Metric | Count |
| --- | ---: |
| Total Graph Nodes | **4,239** |
| Overview (Atlas) Nodes | **413** |
| Story Core Nodes | **1,954** |
| Total Graph Edges | **20,280** |
| Relationship Types | **13** |
| Curated Quest Walkthroughs (RU & EN) | **81** |
| Encyclopedia Entries (RU & EN) | **4,239** |
| Packed Atlas Icons | **377** |

<details>
<summary>Breakdown by Entity Category and Expansion Module</summary>

| Entity Category | Count |
| --- | ---: |
| Characters | 1,603 |
| Items | 1,059 |
| Objects | 877 |
| Locations | 576 |
| Quests | 81 |
| Events | 43 |

| Module / DLC | Nodes |
| --- | ---: |
| Fallout 3 (Base Game) | 3,090 |
| The Pitt | 305 |
| Broken Steel | 269 |
| Operation: Anchorage | 235 |
| Point Lookout | 223 |
| Mothership Zeta | 117 |

</details>

## Tech Stack

- **Frontend**: React 19, TypeScript 5.7, Vite 6, Tailwind CSS 4
- **3D Rendering & Graph**: Three.js (`OrbitControls`), Graphology, Lucide React
- **Data Pipeline**: Python 3 scripts in `scripts/` (ESM/BSA parsing, icon atlas packing, 3D layout enrichment, encyclopedia generation, and localization)

## Getting Started

### Prerequisites
- **Node.js** 18+ and **npm**

### Run Locally
```bash
git clone https://github.com/harriedgemusic/f3-graph.git
cd f3-graph
npm install
npm run dev
```

### Build for Production
```bash
npm run build
npm run preview
```

> **Note:** All prebuilt JSON datasets (`public/data/`) and icon atlases (`public/icons/`) are included in the repository, so you do not need local Fallout 3 game files to run or build the web application.

## Project Structure

```text
f3-graph/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── public/
│   ├── data/
│   │   ├── graph.json             # 4,239 nodes & 20,280 edges with 3D Galaxy/Map coords
│   │   ├── details.json           # Russian encyclopedia entries (4,239)
│   │   ├── details.en.json        # English encyclopedia entries (4,239)
│   │   ├── walkthroughs.json      # Russian quest walkthroughs (81)
│   │   └── walkthroughs.en.json   # English quest walkthroughs (81)
│   └── icons/
│       ├── atlas.png              # Packed Pip-Boy icon texture atlas
│       ├── atlas.json             # UV coordinates for 377 icons
│       └── *.png                  # Extracted DDS-to-PNG game icons
├── scripts/                       # ESM/BSA extraction, dataset & localization pipeline
└── src/
    ├── App.tsx                    # Main shell, navigation tabs, RU/EN switcher
    ├── constants.ts               # Entity, DLC, edge, and subtype metadata
    ├── i18n.tsx                   # Bilingual UI strings and localization context
    ├── types.ts                   # TypeScript interfaces for graph, details & quests
    ├── data/useFalloutData.ts     # Data loader with language caching & adjacency index
    └── components/
        ├── GraphView.tsx          # Interactive Three.js 3D Galaxy / Map renderer
        ├── InspectorPanel.tsx     # Node inspector, isolation & path triggers
        ├── WalkthroughsView.tsx   # Quest archive, checklists & ESM logs
        ├── CatalogView.tsx        # Searchable entity encyclopedia
        ├── EncyclopediaDetailsBlock.tsx
        ├── EntityIcon.tsx
        └── StatsView.tsx          # World analytics & top hubs
```

## Disclaimer

This is a fan-made, non-commercial educational and reference project. *Fallout 3*, *Fallout 3: Game of the Year Edition*, and all related trademarks, characters, lore, and assets are the property of Bethesda Softworks LLC / ZeniMax Media Inc.
