import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { createHttpApi } from './api/client'
import './styles.css'

createRoot(document.getElementById('root') as HTMLElement).render(
  <StrictMode>
    <App api={createHttpApi()} />
  </StrictMode>,
)
