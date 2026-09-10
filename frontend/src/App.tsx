import { Routes, Route } from 'react-router-dom'

function Dashboard() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900">Customer Intelligence Platform</h1>
      <p className="mt-4 text-gray-600">Frontend Foundation successfully initialized.</p>
    </div>
  )
}

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        <Route path="/" element={<Dashboard />} />
      </Routes>
    </div>
  )
}

export default App
