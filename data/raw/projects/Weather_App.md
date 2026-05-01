# Weather App Technical Overview

## Stack and tooling
- Frontend framework: React 18 (JSX, functional components, hooks).
- Build tool: Vite (ES modules, fast dev server, optimized production builds).
- HTTP clients: native `fetch` (city search, current weather), `axios` (forecast).
- Deployment: GitHub Pages via `gh-pages` and a GitHub Actions workflow.
- Linting: ESLint with React, React Hooks, and React Refresh plugins.

## Project structure (high level)
- `index.html` is the entry HTML shell and loads the root React app.
- `src/main.jsx` bootstraps React and renders `App` into `#root`.
- `src/App.jsx` is the top-level composition: ToolBar + WeatherDetails.
- `src/components/ToolBar/ToolBar.jsx` hosts the search UI.
- `src/components/ToolBar/SearchBar/` contains the search logic and styling.
- `src/components/Weather/Weather.jsx` renders current weather details.
- `src/components/Weather/Forecast/forecast.jsx` renders the forecast list.
- `src/config/config.jsx` defines API base URLs.
- `src/index.css` defines global styling.
- `src/App.css` exists but is currently empty.

## Runtime architecture and data flow
### Entry and render flow
1. `index.html` loads a Google Fonts stylesheet (Poppins) and sets the page title and favicon.
2. `src/main.jsx` calls `createRoot(...).render(<App />)`.
3. `App` renders two main sections:
   - `ToolBar`, which provides city search and selection.
   - `WeatherDetails`, which fetches and displays weather data once a city is selected.

### Top-level state in `App`
- `App` maintains `userSelection` in React state.
- `setUserSelection` is passed down to `ToolBar` and then into `SearchBar`.
- When `SearchBar` chooses a city, it updates `userSelection`, which triggers weather fetching in `WeatherDetails`.

### SearchBar mechanics (city search and selection)
The search bar implements a debounced search flow with a dropdown and persistence via localStorage.

Key state and behavior:
- `input`: current text field value.
- `debouncedInput`: updated after 500ms of inactivity.
- `results`: list of cities returned by the backend API.
- `dropdownVisible`: controls dropdown visibility.
- `loader`: shows loading state while fetching.
- `apiCall`: flag to avoid re-fetching after a city is selected.

Lifecycle behavior:
1. On initial mount, `SearchBar` checks localStorage for `lat`, `lon`, and `city`.
   - If present, it restores the last selection and updates both the input field and `userSelection`.
2. `input` changes are debounced for 500ms to reduce API calls.
3. On each debounced input:
   - If fewer than 3 characters, no fetch occurs.
   - If the input is already part of the stored city name, it skips re-fetching.
   - Otherwise, it calls the backend API: `GET {SERVER_API}/cities?city={query}`.
4. The dropdown renders:
   - A loader while fetching.
   - A list of city results with country codes.
   - A "No results found" message when empty.
5. When a city is clicked:
   - The input is set to the chosen city name.
   - The dropdown is hidden.
   - `userSelection` is updated.
   - `UpdateLatLon` persists `lat`, `lon`, and `city` into localStorage.

Local storage keys:
- `lat`: latitude string
- `lon`: longitude string
- `city`: city name string

### WeatherDetails mechanics (current weather)
`WeatherDetails` expects `userSelection` with a `value` shaped as `"lat lon"` and a `name`.

Flow:
1. If `userSelection` is missing, the component returns nothing.
2. `lat` and `lon` are extracted from `userSelection.value`.
3. A fetch is executed:
   - `GET {SERVER_API}/weather?lat={lat}&lon={lon}`
4. On success, the response is stored in state and merged with a `city` property derived from the selection.
5. While data is missing, a loader message is shown.
6. Once data is present, the UI renders:
   - City name and weather description.
   - Icon using OpenWeather icon URLs.
   - Temperature, feels-like, wind speed, humidity, and pressure.

### Forecast mechanics
`Forecast` uses `axios` to fetch forecast data.

Flow:
1. If `lat` or `lon` is missing, it returns nothing.
2. The API call is made:
   - `GET {SERVER_API}/weather/forecast?lat={lat}&lon={lon}`
3. The response expects a `list` array of forecast entries.
4. For each entry, the component renders:
   - Date (day/month)
   - Time (AM/PM formatting)
   - OpenWeather icon
   - Temperature
5. The UI is a horizontally scrollable list.

## API integration (client expectations)
The frontend assumes the existence of a backend that exposes three endpoints under `SERVER_API`:
- `GET /cities?city={query}`
  - Expected response shape: `{ data: [{ name, country, latitude, longitude }, ...] }`.
- `GET /weather?lat={lat}&lon={lon}`
  - Expected response shape: OpenWeather current weather format.
- `GET /weather/forecast?lat={lat}&lon={lon}`
  - Expected response shape: OpenWeather forecast format with a `list` array.

The client does not directly use `import.meta.env` or API keys. The README and GitHub Actions secrets mention API keys, which suggests the backend (not in this repo) likely uses those keys to call external services.

## Configuration
`src/config/config.jsx` defines API endpoints:
- `SERVER_API` points to a deployed AWS Lambda URL.
- `LOCAL_SERVER_API` points to `http://localhost:5000/api` for local backend testing.

## Styling and UI
- Global styles are in `src/index.css` and apply the Poppins font to all elements.
- The main UI is styled via component-level CSS files:
  - SearchBar layout, dropdown, responsiveness.
  - Weather details layout and typography.
  - Forecast horizontal scroll list styling.
- `src/App.css` currently contains no styles.

## Build and deployment
### Vite build
- `npm run dev` starts the Vite dev server.
- `npm run build` produces a production build in `dist/`.
- `npm run preview` serves the production build locally.

### GitHub Pages
- `package.json` sets `homepage` to `https://n-saji.github.io/weather_app/`.
- `vite.config.js` sets `base: "/weather_app/"` to match GitHub Pages pathing.
- `npm run deploy` uses `gh-pages` to publish the `dist/` directory.

### CI/CD workflow
`react.yml` defines a GitHub Actions workflow that:
1. Triggers on pushes to `main`.
2. Installs dependencies with Node 18.
3. Builds the app.
4. Deploys with `npm run deploy` using `gh-pages` and GitHub token.
5. Exposes secrets (`GEO_API_KEY`, `WEATHER_API_KEY`) as environment variables for the deploy step.

## Linting
`eslint.config.js` enforces recommended ESLint and React rules, with React Hooks rules and React Refresh warnings for correct hot reload usage.

## Assets
- `src/assets/` contains `vite.svg` (default Vite asset).
- `public/` is currently empty.

## Notes and consistency observations
- README mentions a `.env` file with `REACT_APP_WEATHER_API_KEY`. The frontend code does not reference this key and instead calls the backend API via `SERVER_API`.
- Dependencies such as `express`, `dotenv`, `lottie-react-native`, and `react-select-async-paginate` are listed but are not referenced in the current `src/` code. They may be leftover, planned, or used elsewhere.

## End-to-end behavior summary
1. User loads the app; previous city selection is restored from localStorage.
2. User types a city name; search is debounced and results fetched from the backend.
3. User selects a city; selection is saved in localStorage.
4. Current weather and forecast are fetched in parallel by different components.
5. UI displays current weather details and a scrollable forecast list.
