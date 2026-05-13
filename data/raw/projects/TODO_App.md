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
