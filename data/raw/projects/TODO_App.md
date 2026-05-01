# TODO App


## 1. Project Purpose and Scope

This is a small single-page React application that implements a task list with deadlines, a digital clock, and a light/dark theme toggle. It targets browser use and is deployed as a static site via GitHub Pages.

Key features:
- Create, update, toggle, and delete tasks.
- Set a deadline for each task using a date picker.
- Persist tasks and theme preference in `localStorage`.
- Display a live digital clock that updates every second.
- Provide a light/dark mode UI switch.

## 2. Tech Stack and Tooling

Core stack:
- React 18 for UI and state management.
- Vite for development server, bundling, and production builds.
- ESLint for linting, with React and React Hooks rules enabled.
- gh-pages for deploying the built `dist` output to GitHub Pages.

Source of configuration:
- Vite config: [vite.config.js](vite.config.js)
- ESLint config: [eslint.config.js](eslint.config.js)
- Project metadata and scripts: [package.json](package.json)

## 3. Build, Run, and Deploy

Scripts from [package.json](package.json):
- `dev`: starts the Vite dev server.
- `build`: builds a production bundle into `dist`.
- `preview`: runs a preview server for the build output.
- `lint`: runs ESLint on the codebase.
- `predeploy`: builds before deployment.
- `deploy`: pushes `dist` to GitHub Pages using `gh-pages`.

GitHub Pages configuration:
- The app base URL is set in [vite.config.js](vite.config.js) via `base: "/ToDo-App/"`.
- `homepage` in [package.json](package.json) matches the GitHub Pages URL.

## 4. Runtime Entry and App Composition

Application entry points:
- [index.html](index.html) provides the root DOM node and links the Google Fonts used.
- [src/main.jsx](src/main.jsx) creates the React root and renders the app within `StrictMode`.
- [src/App.jsx](src/App.jsx) is the top-level component and only renders `RenderTask`.

Basic composition:
- `App` -> `RenderTask` -> `DigitalClock` and task UI.

## 5. Component Breakdown

### 5.1. `RenderTask` Component

Source: [src/components/render_task.jsx](src/components/render_task.jsx)

Responsibilities:
- Controls the overall UI for the TODO list.
- Manages all task-related state (task text, deadline, task list).
- Manages and persists dark mode state.
- Handles add, update, toggle, delete, and save actions.

State variables:
- `task`: current input text for a new task.
- `deadline`: current input date for a new task. Defaults to today in ISO format.
- `tasks`: array of task objects, each containing:
  - `id`: a random number from `Math.random()`.
  - `task`: string content.
  - `completed`: boolean flag.
  - `deadline`: string date (YYYY-MM-DD).
- `darkMode`: boolean theme toggle.

Initialization behavior (on mount):
- Loads `tasks` from `localStorage` under the key `tasks`, if present.
- Loads `darkMode` from `localStorage` under the key `darkMode`, if present.
- Applies theme background changes immediately when `darkMode` is loaded.

Actions and helpers:
- `addTask()`:
  - Validates that `task` and `deadline` are not empty.
  - Creates a new task object and appends it to `tasks`.
  - Resets `task` to empty string and `deadline` back to today.
- `updateTask(index)`:
  - Uses `prompt` to replace the task string.
  - Rejects empty input; keeps existing task if empty.
- `toggleTask(index)`:
  - Flips the `completed` flag for the selected task.
- `deleteTask(id)`:
  - Removes the task with a matching `id`.
- `saveList()`:
  - Writes the current `tasks` array into `localStorage`.
- `toggleDarkMode(v)`:
  - Mutates `document.body.style.backgroundColor` to black or white.
  - Adds a smooth transition for theme switching.
  - Writes `darkMode` to `localStorage`.

Keyboard behavior:
- A global `onkeydown` handler listens for `Enter` and invokes `addTask()`.
- This attaches to the global window scope (no explicit `useEffect`).

UI and layout:
- A top header holds the clock and theme selector.
- A form row for task input, date input, and add button.
- A table with the task list and action buttons.
- A final "Save List" button to persist tasks.

Theme usage:
- Inline styles apply dynamic text and background colors based on `darkMode`.
- The `select` value is controlled by `darkMode` and toggles with user input.

Note on import casing:
- `DigitalClock` is imported using `./digitalCLock` (case differs from file name).
- This can be case-sensitive on some file systems; macOS typically ignores case.

### 5.2. `DigitalClock` Component

Source: [src/components/digitalClock.jsx](src/components/digitalClock.jsx)

Responsibilities:
- Displays a live clock that updates every second.
- Adapts text color based on dark mode.

Key implementation details:
- Uses `useEffect` with `setInterval` to update time every 1000 ms.
- `formatTime()` converts hours to 12-hour format and appends AM/PM.
- `padZero()` ensures hours, minutes, and seconds are two digits.
- Accepts a prop `darkMode` (passed as `mode.darkMode`) for color switching.

## 6. State and Data Flow

Data flow is simple and local to components:
- `RenderTask` holds all state.
- `DigitalClock` is controlled by a `darkMode` prop.
- There is no global state library, backend, or API calls.

Task object schema (in-memory and persisted):
```
{
  id: number,
  task: string,
  completed: boolean,
  deadline: string // YYYY-MM-DD
}
```

Persistence:
- `tasks` stored as JSON in `localStorage`.
- `darkMode` stored as JSON in `localStorage`.

## 7. Styling and UI

Global styles:
- [src/index.css](src/index.css) sets the base font to Roboto.
- The font is loaded from Google Fonts in [index.html](index.html).

Component styles:
- [src/components/digitalClock.css](src/components/digitalClock.css)
  - Centers the clock and sets font size/weight.
- [src/components/render_task.css](src/components/render_task.css)
  - Layout for header, input row, table, buttons, and responsive rules.

Theme-related styling:
- Many colors are set inline in React to react to `darkMode` state.
- The dark theme uses darker backgrounds and light text for readability.
- A smooth transition is used to avoid abrupt changes.

Responsive design:
- Media query at `max-width: 1000px` reduces font sizes, input widths,
  and button sizes to improve mobile experience.

## 8. Linting and Code Quality

ESLint configuration in [eslint.config.js](eslint.config.js):
- Uses recommended ESLint rules and React-specific rules.
- Enforces React Hooks best practices.
- Enables React Refresh checks for better fast-refresh safety.

## 9. Deployment Context

The project is configured for GitHub Pages:
- Build output is placed in `dist`.
- `gh-pages` publishes the `dist` folder.
- The base path is set to `/ToDo-App/` so assets resolve correctly.

## 10. Notable Implementation Details and Behavior

- The task list is only persisted when the user clicks "Save List".
  If the user refreshes before saving, new tasks are not stored.
- The `Enter` key handler is global and triggers task addition from any focus state.
- The app uses `Math.random()` for task IDs, which is simple but not stable across sessions.
- The `updateTask` flow uses a `prompt`, which is synchronous and blocks the UI.
- `darkMode` toggles the document body background directly; text colors are set inline.

## 11. Key Files Summary

- App shell and entry: [index.html](index.html), [src/main.jsx](src/main.jsx)
- Top-level component: [src/App.jsx](src/App.jsx)
- Task UI and logic: [src/components/render_task.jsx](src/components/render_task.jsx)
- Clock widget: [src/components/digitalClock.jsx](src/components/digitalClock.jsx)
- Styling: [src/index.css](src/index.css), [src/components/render_task.css](src/components/render_task.css), [src/components/digitalClock.css](src/components/digitalClock.css)
- Tooling config: [package.json](package.json), [vite.config.js](vite.config.js), [eslint.config.js](eslint.config.js)
