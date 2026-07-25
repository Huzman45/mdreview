## ADDED Requirements

### Requirement: The colour scheme can be chosen explicitly
The interface SHALL offer light, dark, and follow-the-system options, because the
operating system preference is often wrong for the room the reviewer is sitting in.

#### Scenario: Choosing dark on a light system
- **GIVEN** the operating system prefers a light scheme
- **WHEN** the reviewer selects dark
- **THEN** the interface renders in dark colours

#### Scenario: Choosing light on a dark system
- **GIVEN** the operating system prefers a dark scheme
- **WHEN** the reviewer selects light
- **THEN** the interface renders in light colours

#### Scenario: Following the system
- **WHEN** the reviewer selects the system option
- **THEN** the interface renders according to the operating system preference
- **AND** it changes if that preference changes

#### Scenario: Default is to follow the system
- **WHEN** a reviewer with no stored preference opens a page
- **THEN** the interface follows the operating system preference

### Requirement: The choice is remembered
The selected scheme SHALL persist across page navigations and across browser sessions.
A preference that has to be reset on every page would be worse than none.

#### Scenario: Preference persists across pages
- **WHEN** the reviewer selects a scheme and opens a different document
- **THEN** the selected scheme is still in effect

#### Scenario: Preference persists across visits
- **WHEN** the reviewer selects a scheme, closes the browser, and returns
- **THEN** the selected scheme is still in effect

### Requirement: The chosen scheme applies before first paint
The stored preference SHALL be applied before the page is first painted. Reading it
after the page renders would show a flash of the wrong colours on every load.

#### Scenario: No flash of the wrong scheme
- **WHEN** a page loads with a stored preference that differs from the system
  preference
- **THEN** the stored scheme is applied before the page is first painted

### Requirement: The control communicates the active scheme
The control SHALL indicate which scheme is currently selected, and MUST be reachable
from every page type.

#### Scenario: Control reflects the current choice
- **WHEN** the reviewer has chosen a scheme
- **THEN** the control indicates which of light, dark, or system is active

#### Scenario: Control is reachable on every page
- **WHEN** the reviewer is on the index, a document, a raw view, or a comparison
- **THEN** the theme control is present
