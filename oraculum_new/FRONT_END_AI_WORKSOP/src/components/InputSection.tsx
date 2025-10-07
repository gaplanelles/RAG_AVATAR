import React from 'react';

interface InputSectionProps {
  userInput: string;
  setUserInput: (value: string) => void;
  handleSpeak: () => void;
}

const InputSection: React.FC<InputSectionProps> = ({ userInput, setUserInput, handleSpeak }) => {
  return (
    <div className="input-section">
      <input
        type="text"
        value={userInput}
        onChange={(e) => setUserInput(e.target.value)}
        placeholder="Enter text for avatar to speak"
      />
      <button onClick={handleSpeak}>Speak</button>
    </div>
  );
};

export default InputSection;