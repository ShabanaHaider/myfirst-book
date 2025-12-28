# Quick Start - Chatbot in Docusaurus Book

## 🎉 What's New

Your Docusaurus book now has an **AI-powered chatbot** that appears as a floating icon on every page!

## 🚀 How to Start Everything

### Terminal 1 - Backend API:
```bash
cd D:\projects\myfirst_book\backend
python run_server.py
```
✅ Backend running on: http://localhost:8001

### Terminal 2 - Docusaurus Book:
```bash
cd D:\projects\myfirst_book\my-book
npm start
```
✅ Book running on: http://localhost:3000

## 📖 How to Use the Chatbot

1. **Open your book**: http://localhost:3000
2. **Look for the purple chat button** in the bottom-right corner 💬
3. **Click it** to open the chat interface
4. **Ask a question** like:
   - "What are humanoid robots?"
   - "Tell me about ROS"
   - "How does AI perception work?"
5. **Get instant answers** from your documentation!

## ✨ What Users Will See

```
┌─────────────────────────────────────────┐
│  Your Docusaurus Book Content          │
│                                         │
│  [Documentation pages...]               │
│                                         │
│                                    ┌──┐ │
│                                    │💬│ │ ← Floating Chat Button
│                                    └──┘ │
└─────────────────────────────────────────┘
```

When clicked:

```
┌─────────────────────────────────────────┐
│  Your Docusaurus Book Content          │
│                                         │
│                              ┌─────────┐│
│                              │ AI Chat ││
│                              │         ││
│                              │ User: Q ││
│                              │ AI: A   ││
│                              │         ││
│                              │ [Input] ││
│                              └─────────┘│
└─────────────────────────────────────────┘
```

## 🎨 Features

- ✅ Beautiful gradient design (purple)
- ✅ Smooth animations
- ✅ Dark mode support
- ✅ Mobile responsive
- ✅ Loading indicators
- ✅ Error handling
- ✅ Auto-scroll messages
- ✅ Accessible (ARIA labels)

## 🔧 Configuration

**Backend API URL**: Configured in `my-book/.env`
```env
REACT_APP_API_BASE_URL=http://localhost:8001
```

**CORS**: Already configured in backend for ports 3000 and 3001

## 📁 Files Created

```
my-book/
├── src/
│   ├── components/ChatBot/
│   │   ├── ChatBot.js          # Main component
│   │   ├── ChatBot.module.css  # Styles
│   │   └── index.js            # Export
│   └── theme/
│       └── Root.js             # Global wrapper
└── .env                        # API configuration
```

## 🐛 Troubleshooting

### Chatbot not appearing?
```bash
cd my-book
npm run clear
npm start
```

### CORS errors?
- Restart backend server
- Check CORS config in `backend/src/main.py`

### Can't send messages?
- Verify backend is running on port 8001
- Check browser console for errors

## 📚 Documentation

- **Full Integration Guide**: `CHATBOT_INTEGRATION.md`
- **General Chatbot Guide**: `CHATBOT_GUIDE.md`

## 🎊 You're All Set!

Your documentation is now interactive with AI assistance!

Users can read your book and get instant help by clicking the chat button. Perfect for learning about humanoid robotics! 🤖
