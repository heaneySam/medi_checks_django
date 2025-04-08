# Critical Meds Management System

A Django-based system for managing critical medications and patient information in healthcare settings.

## Features

- Patient Management
  - Add and view patient details
  - Track NHS and hospital numbers
  - Modern modal-based interface
  - Real-time updates with HTMX

## Tech Stack

- Django 5.0.1
- Alpine.js for interactive UI
- HTMX for dynamic updates
- Tailwind CSS for styling

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/critical_meds_django.git
cd critical_meds_django
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Start the development server:
```bash
python manage.py runserver
```

## Development

- The project uses Alpine.js for modal interactions
- HTMX is used for form submissions and dynamic content updates
- Tailwind CSS provides the styling framework

## License

MIT License
