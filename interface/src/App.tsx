import { useState } from 'react';
import './App.css';

function Star({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="#e9b8cb">
      <path d="M50 0 C53 38 62 47 100 50 C62 53 53 62 50 100 C47 62 38 53 0 50 C38 47 47 38 50 0 Z" />
    </svg>
  );
}

const SPARKLES = [
  { top: '4%',  left: '46%', size: 10, delay: 0.0 },
  { top: '12%', left: '22%', size: 16, delay: 0.5 },
  { top: '10%', left: '70%', size: 18, delay: 1.1 },
  { top: '48%', left: '82%', size: 9,  delay: 0.8 },
  { top: '78%', left: '68%', size: 13, delay: 0.3 },
  { top: '80%', left: '26%', size: 10, delay: 1.4 },
];

function App() {
  const [listening, setListening] = useState(false);
  const [question, setQuestion] = useState<string | null>(null);
  const [answer, setAnswer] = useState<string | null>(null);

  const handleTalk = () => {
    // Étape suivante : pont Python (record -> STT -> llama-server)
    setListening(v => !v);
  };

  return (
    <div className="app">
      <div className={`card ${listening ? 'listening' : ''}`} onClick={handleTalk}>
        <div className="stars">
          <div className="star-main"><Star size={110} /></div>
          {SPARKLES.map((s, i) => (
            <div key={i} className="sparkle"
              style={{ top: s.top, left: s.left, animationDelay: `${s.delay}s` }}>
              <Star size={s.size} />
            </div>
          ))}
        </div>

        <div className="conversation">
          {question && <p className="q">« {question} »</p>}
          {answer && <p className="a">{answer}</p>}
        </div>
      </div>

      <button className="glass-btn glass-left" aria-label="bouton gauche" />
      <button className="glass-btn glass-right" aria-label="bouton droit" />
    </div>
  );
}

export default App;
