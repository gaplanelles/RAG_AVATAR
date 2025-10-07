# RAG Frontend

This is the frontend application for the RAG system, built with ReactJS.

## Prerequisites

Before you begin, you need to install:

1. **Node.js and npm**:
   - Windows/macOS: Download and install from [Node.js official website](https://nodejs.org/)
   - Linux (Ubuntu/Debian):
     ```bash
     sudo apt update
     sudo apt install nodejs npm
     ```

2. **Verify installations**:
   ```bash
   node --version
   npm --version
   ```
   Both commands should display version numbers if installed correctly.

## Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/fsabiu/RAG-frontend.git
   cd RAG-frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   npm install react-scripts
   ```
   This will install all required packages defined in package.json.

3. **Environment Setup**:
   - The application uses default configuration for API endpoints
   - If you need to modify API endpoints, update them in:
     ```javascript
     src/config/apiConfig.js
     ```

4. **Start the application**:
   ```bash
   npm start
   ```
   The application will run on [http://localhost:3000](http://localhost:3000)

## Project Structure

- `public/`: Static files
  - `index.html`: Main HTML file
  - `images/`: Application images
- `src/`: Source code
  - `components/`: React components
  - `config/`: Configuration files
  - `pages/`: Page components
  - `styles/`: CSS styles
  - `utils/`: Utility functions

## Available Scripts

- `npm start`: Runs the app in development mode
- `npm build`: Builds the app for production
- `npm test`: Runs the test suite
- `npm eject`: Ejects from create-react-app

## Troubleshooting

Common issues and solutions:

1. **Node.js version conflicts**:
   ```bash
   nvm install 18
   nvm use 18
   ```

2. **Port 3000 already in use**:
   ```bash
   kill -9 $(lsof -t -i:3000)
   # or
   npm start -- --port 3001
   ```

3. **Module not found errors**:
   ```bash
   rm -rf node_modules
   npm cache clean --force
   npm install
   ```

## Best Practices

- Use small, reusable components
- Manage state effectively
- Write tests for components
- Maintain code quality with ESLint and Prettier

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
