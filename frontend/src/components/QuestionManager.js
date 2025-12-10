import React, { useState, useEffect } from 'react';
import './QuestionManager.css';
import { API_URL, fetchAuthAPI } from '../config';

function QuestionManager({ onBack }) {
  const [questionSets, setQuestionSets] = useState([]);
  const [selectedSet, setSelectedSet] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showNewSetForm, setShowNewSetForm] = useState(false);
  const [showQuestionForm, setShowQuestionForm] = useState(false);
  const [newSetName, setNewSetName] = useState('');
  const [editingQuestion, setEditingQuestion] = useState(null);
  const [availableImages, setAvailableImages] = useState([]);

  // Form state for question
  const [questionForm, setQuestionForm] = useState({
    day_number: 1,
    question_text: '',
    correct_answer: '',
    image_1: '',
    image_2: '',
    image_3: '',
    image_4: '',
    image_5: ''
  });

  // Image source type (local or url) for each image slot
  const [imageSourceType, setImageSourceType] = useState({
    image_1: 'url',
    image_2: 'url',
    image_3: 'url',
    image_4: 'url',
    image_5: 'url'
  });

  useEffect(() => {
    fetchQuestionSets();
    fetchAvailableImages();
  }, []);

  useEffect(() => {
    if (selectedSet) {
      fetchQuestions(selectedSet.id);
    }
  }, [selectedSet]);

  const fetchQuestionSets = async () => {
    setLoading(true);
    try {
      const response = await fetchAuthAPI(`${API_URL}/api/question-sets`);
      if (response.ok) {
        const data = await response.json();
        setQuestionSets(data.question_sets || []);
      }
    } catch (err) {
      console.error('Error fetching question sets:', err);
      setError('Failed to load question sets');
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableImages = async () => {
    try {
      const response = await fetchAuthAPI(`${API_URL}/api/images`);
      if (response.ok) {
        const data = await response.json();
        setAvailableImages(data.images || []);
      }
    } catch (err) {
      console.error('Error fetching available images:', err);
    }
  };

  const fetchQuestions = async (setId) => {
    try {
      const response = await fetchAuthAPI(`${API_URL}/api/question-sets/${setId}/questions`);
      if (response.ok) {
        const data = await response.json();
        setQuestions(data.questions || []);
      }
    } catch (err) {
      console.error('Error fetching questions:', err);
      setError('Failed to load questions');
    }
  };

  const handleCreateSet = async (e) => {
    e.preventDefault();
    if (!newSetName.trim()) return;

    try {
      const response = await fetchAuthAPI(`${API_URL}/api/question-sets`, {
        method: 'POST',
        body: JSON.stringify({ name: newSetName })
      });

      if (response.ok) {
        const data = await response.json();
        await fetchQuestionSets();
        setNewSetName('');
        setShowNewSetForm(false);
        // Select the newly created set
        const newSet = questionSets.find(s => s.id === data.question_set_id);
        if (newSet) setSelectedSet(newSet);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to create question set');
      }
    } catch (err) {
      console.error('Error creating question set:', err);
      setError('Failed to create question set');
    }
  };

  const handleDeleteSet = async (setId) => {
    if (!window.confirm('Are you sure you want to delete this question set? This will delete all questions in it.')) {
      return;
    }

    try {
      const response = await fetchAuthAPI(`${API_URL}/api/question-sets/${setId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        await fetchQuestionSets();
        if (selectedSet?.id === setId) {
          setSelectedSet(null);
          setQuestions([]);
        }
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to delete question set');
      }
    } catch (err) {
      console.error('Error deleting question set:', err);
      setError('Failed to delete question set');
    }
  };

  const handleSetDefault = async (setId) => {
    try {
      const response = await fetchAuthAPI(`${API_URL}/api/question-sets/${setId}/default`, {
        method: 'PUT'
      });

      if (response.ok) {
        await fetchQuestionSets();
      }
    } catch (err) {
      console.error('Error setting default:', err);
      setError('Failed to set default question set');
    }
  };

  const handleSaveQuestion = async (e) => {
    e.preventDefault();
    
    // If editing, use update function instead
    if (editingQuestion) {
      return handleUpdateQuestion(e);
    }
    
    if (!selectedSet) return;

    try {
      const response = await fetchAuthAPI(
        `${API_URL}/api/question-sets/${selectedSet.id}/questions`,
        {
          method: 'POST',
          body: JSON.stringify(questionForm)
        }
      );

      if (response.ok) {
        await fetchQuestions(selectedSet.id);
        await fetchQuestionSets(); // Refresh to update question count
        resetQuestionForm();
        setShowQuestionForm(false);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to save question');
      }
    } catch (err) {
      console.error('Error saving question:', err);
      setError('Failed to save question');
    }
  };

  const resetQuestionForm = () => {
    setQuestionForm({
      day_number: 1,
      question_text: '',
      correct_answer: '',
      image_1: '',
      image_2: '',
      image_3: '',
      image_4: '',
      image_5: ''
    });
    setEditingQuestion(null);
    setImageSourceType({
      image_1: 'url',
      image_2: 'url',
      image_3: 'url',
      image_4: 'url',
      image_5: 'url'
    });
  };

  const handleEditQuestion = (question) => {
    setQuestionForm({
      day_number: question.day_number,
      question_text: question.question_text,
      correct_answer: question.correct_answer,
      image_1: question.image_1 || '',
      image_2: question.image_2 || '',
      image_3: question.image_3 || '',
      image_4: question.image_4 || '',
      image_5: question.image_5 || ''
    });
    
    // Detect if images are local or external URLs
    const newImageSourceType = {};
    for (let i = 1; i <= 5; i++) {
      const imageUrl = question[`image_${i}`] || '';
      // If URL starts with /images/, it's local, otherwise it's external
      newImageSourceType[`image_${i}`] = imageUrl.startsWith('/images/') ? 'local' : 'url';
    }
    setImageSourceType(newImageSourceType);
    
    setEditingQuestion(question);
    setShowQuestionForm(true);
  };

  const handleUpdateQuestion = async (e) => {
    e.preventDefault();
    if (!selectedSet || !editingQuestion) return;

    try {
      const response = await fetchAuthAPI(
        `${API_URL}/api/question-sets/${selectedSet.id}/questions/${editingQuestion.day_number}`,
        {
          method: 'PUT',
          body: JSON.stringify(questionForm)
        }
      );

      if (response.ok) {
        await fetchQuestions(selectedSet.id);
        await fetchQuestionSets();
        resetQuestionForm();
        setShowQuestionForm(false);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update question');
      }
    } catch (err) {
      console.error('Error updating question:', err);
      setError('Failed to update question');
    }
  };

  const handleDeleteQuestion = async (dayNumber) => {
    if (!window.confirm(`Are you sure you want to delete the question for Day ${dayNumber}?`)) {
      return;
    }

    try {
      const response = await fetchAuthAPI(
        `${API_URL}/api/question-sets/${selectedSet.id}/questions/${dayNumber}`,
        {
          method: 'DELETE'
        }
      );

      if (response.ok) {
        await fetchQuestions(selectedSet.id);
        await fetchQuestionSets(); // Refresh to update question count
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to delete question');
      }
    } catch (err) {
      console.error('Error deleting question:', err);
      setError('Failed to delete question');
    }
  };

  const getAvailableDays = () => {
    const usedDays = questions.map(q => q.day_number);
    const allDays = Array.from({ length: 24 }, (_, i) => i + 1);
    return allDays.filter(day => !usedDays.includes(day));
  };

  return (
    <div className="question-manager-page">
      <div className="snow-overlay"></div>
      
      <div className="question-manager-container">
        {/* Header */}
        <div className="manager-header">
          <button className="back-button" onClick={onBack}>
            ← Back to Dashboard
          </button>
          <h1>📝 Question Manager</h1>
        </div>

        {error && (
          <div className="manager-error">
            {error}
            <button onClick={() => setError('')}>×</button>
          </div>
        )}

        <div className="manager-content">
          {/* Left Panel - Question Sets */}
          <div className="sets-panel">
            <div className="panel-header">
              <h2>Question Sets</h2>
              <button 
                className="new-set-button"
                onClick={() => setShowNewSetForm(!showNewSetForm)}
              >
                + New Set
              </button>
            </div>

            {showNewSetForm && (
              <form className="new-set-form" onSubmit={handleCreateSet}>
                <input
                  type="text"
                  value={newSetName}
                  onChange={(e) => setNewSetName(e.target.value)}
                  placeholder="Question Set Name"
                  required
                />
                <div className="form-buttons">
                  <button type="submit">Create</button>
                  <button type="button" onClick={() => {
                    setShowNewSetForm(false);
                    setNewSetName('');
                  }}>Cancel</button>
                </div>
              </form>
            )}

            <div className="sets-list">
              {loading ? (
                <p className="loading-text">Loading...</p>
              ) : questionSets.length === 0 ? (
                <p className="empty-text">No question sets yet. Create one above!</p>
              ) : (
                questionSets.map(set => (
                  <div 
                    key={set.id}
                    className={`set-item ${selectedSet?.id === set.id ? 'active' : ''}`}
                    onClick={() => setSelectedSet(set)}
                  >
                    <div className="set-info">
                      <div className="set-name">
                        {set.name}
                        {set.is_default && <span className="default-badge">⭐ Default</span>}
                      </div>
                      <div className="set-count">{set.question_count}/24 questions</div>
                    </div>
                    <div className="set-actions">
                      {!set.is_default && (
                        <button 
                          className="set-action-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSetDefault(set.id);
                          }}
                          title="Set as default"
                        >
                          ⭐
                        </button>
                      )}
                      <button 
                        className="set-action-btn delete"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteSet(set.id);
                        }}
                        title="Delete set"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Right Panel - Questions */}
          <div className="questions-panel">
            {selectedSet ? (
              <>
                <div className="panel-header">
                  <h2>Questions for "{selectedSet.name}"</h2>
                  <button 
                    className="add-question-button"
                    onClick={() => {
                      const availableDays = getAvailableDays();
                      if (availableDays.length > 0) {
                        setQuestionForm({...questionForm, day_number: availableDays[0]});
                      }
                      setShowQuestionForm(!showQuestionForm);
                    }}
                    disabled={questions.length >= 24}
                  >
                    + Add Question
                  </button>
                </div>

                {showQuestionForm && (
                  <form className="question-form" onSubmit={handleSaveQuestion}>
                    <h3>{editingQuestion ? `Edit Question for Day ${editingQuestion.day_number}` : 'Add New Question'}</h3>
                    
                    <div className="form-group">
                      <label>Day Number (1-24)</label>
                      <select
                        value={questionForm.day_number}
                        onChange={(e) => setQuestionForm({...questionForm, day_number: parseInt(e.target.value)})}
                        required
                        disabled={editingQuestion !== null}
                      >
                        {editingQuestion ? (
                          <option value={questionForm.day_number}>Day {questionForm.day_number}</option>
                        ) : (
                          getAvailableDays().map(day => (
                            <option key={day} value={day}>Day {day}</option>
                          ))
                        )}
                      </select>
                    </div>

                    <div className="form-group">
                      <label>Question Text</label>
                      <textarea
                        value={questionForm.question_text}
                        onChange={(e) => setQuestionForm({...questionForm, question_text: e.target.value})}
                        placeholder="Enter your question..."
                        required
                        rows="3"
                      />
                    </div>

                    <div className="form-group">
                      <label>Correct Answer</label>
                      <input
                        type="text"
                        value={questionForm.correct_answer}
                        onChange={(e) => setQuestionForm({...questionForm, correct_answer: e.target.value})}
                        placeholder="Enter the correct answer"
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label>Image URLs (Optional)</label>
                      <p className="image-hint">Choose local images from the backend folder or enter external URLs</p>
                      {[1, 2, 3, 4, 5].map(num => (
                        <div key={num} className="image-input-group">
                          <div className="image-source-toggle">
                            <label className="radio-label">
                              <input
                                type="radio"
                                name={`image_${num}_source`}
                                value="local"
                                checked={imageSourceType[`image_${num}`] === 'local'}
                                onChange={() => setImageSourceType({...imageSourceType, [`image_${num}`]: 'local'})}
                              />
                              <span>Local Image</span>
                            </label>
                            <label className="radio-label">
                              <input
                                type="radio"
                                name={`image_${num}_source`}
                                value="url"
                                checked={imageSourceType[`image_${num}`] === 'url'}
                                onChange={() => setImageSourceType({...imageSourceType, [`image_${num}`]: 'url'})}
                              />
                              <span>External URL</span>
                            </label>
                          </div>
                          
                          {imageSourceType[`image_${num}`] === 'local' ? (
                            <select
                              value={questionForm[`image_${num}`]}
                              onChange={(e) => setQuestionForm({...questionForm, [`image_${num}`]: e.target.value})}
                              className="image-select"
                            >
                              <option value="">-- Select Image {num} --</option>
                              {availableImages.map(img => (
                                <option key={img.name} value={img.url}>
                                  {img.name}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <input
                              type="url"
                              value={questionForm[`image_${num}`]}
                              onChange={(e) => setQuestionForm({...questionForm, [`image_${num}`]: e.target.value})}
                              placeholder={`Image ${num} external URL (https://...)`}
                              className="image-url-input"
                            />
                          )}
                        </div>
                      ))}
                    </div>

                    <div className="form-buttons">
                      <button type="submit" className="save-btn">
                        {editingQuestion ? 'Update Question' : 'Save Question'}
                      </button>
                      <button type="button" className="cancel-btn" onClick={() => {
                        setShowQuestionForm(false);
                        resetQuestionForm();
                      }}>Cancel</button>
                    </div>
                  </form>
                )}

                <div className="questions-list">
                  {questions.length === 0 ? (
                    <p className="empty-text">No questions in this set yet. Add one above!</p>
                  ) : (
                    <div className="questions-grid">
                      {questions.sort((a, b) => a.day_number - b.day_number).map(q => (
                        <div key={q.id} className="question-card">
                          <div className="question-card-header">
                            <div className="question-day">Day {q.day_number}</div>
                            <div className="question-card-actions">
                              <button 
                                className="edit-question-btn"
                                onClick={() => handleEditQuestion(q)}
                                title="Edit this question"
                              >
                                ✏️
                              </button>
                              <button 
                                className="delete-question-btn"
                                onClick={() => handleDeleteQuestion(q.day_number)}
                                title="Delete this question"
                              >
                                🗑️
                              </button>
                            </div>
                          </div>
                          <div className="question-text">{q.question_text}</div>
                          <div className="question-answer">
                            <strong>Answer:</strong> {q.correct_answer}
                          </div>
                          {q.images && q.images.length > 0 && (
                            <div className="question-images">
                              📷 {q.images.length} image(s)
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {questions.length < 24 && (
                  <div className="progress-info">
                    {questions.length}/24 questions complete
                    <div className="progress-bar">
                      <div 
                        className="progress-fill" 
                        style={{width: `${(questions.length / 24) * 100}%`}}
                      />
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="no-set-selected">
                <p>👈 Select a question set to view and manage questions</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default QuestionManager;
