import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './App.css'

function App() {
  const [messages, setMessages] = useState([
    { 
      sender: 'bot', 
      text: 'SYSTEM_READY...\nIdentity: Dunder Mifflin AI Auditor (Toby_V2.0).\n\nSelect Protocol:\n* Compliance_Check\n* Conspiracy_Detection\n* Financial_Forensics' 
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  
  // Ref para auto-scroll
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim()) return

    const userMsg = { sender: 'user', text: input }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const response = await axios.post('http://localhost:8000/chat', {
        message: input
      })

      const botMsg = { sender: 'bot', text: response.data.response }
      setMessages((prev) => [...prev, botMsg])
    } catch (error) {
      console.error("Erro:", error)
      const errorMsg = { sender: 'bot', text: '❌ **SYSTEM_ERROR**: Connection lost with Mainframe.' }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') sendMessage()
  }

  return (
    <div className="cyber-container">
      {/* Efeito de Scanline na tela inteira */}
      <div className="scanlines"></div>

      <header className="cyber-header">
        <h1 className="glitch-text" data-text="AUDITOR_V.2.0">👾 Agente Auditor Dunder Mifflin</h1>
      </header>
      
      <div className="cyber-messages-area">
        {messages.map((msg, index) => (
          <div key={index} className={`cyber-bubble ${msg.sender}`}>
            <div className="bubble-header">
              <span className="user-label">{msg.sender === 'bot' ? 'TOBY_AI' : 'USER_ID'}</span>
              <span className="timestamp">{new Date().toLocaleTimeString()}</span>
            </div>
            <div className="markdown-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.text}
              </ReactMarkdown>
            </div>
          </div>
        ))}
        
        {/* CORREÇÃO AQUI: Colocamos as aspas para proteger os sinais de maior que */}
        {loading && <div className="loading-cyber">{'>>>'} Processando o pedido...</div>}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="cyber-input-area">
        <span className="prompt-char">{'>'}</span>
        <input 
          type="text" 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="O que deseja saber?"
          disabled={loading}
          autoFocus
        />
        <button onClick={sendMessage} disabled={loading}>
          EXECUTAR
        </button>
      </div>
    </div>
  )
}

export default App