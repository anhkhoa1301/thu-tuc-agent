import { useState, useRef, useEffect } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, FlatList,
  KeyboardAvoidingView, Platform, ActivityIndicator,
  StyleSheet, ListRenderItem,
} from 'react-native'
import Markdown from 'react-native-markdown-display'
import { AGENT_ENDPOINT } from '../constants'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

const SUGGESTED = [
  'Làm căn cước công dân cần giấy tờ gì?',
  'Đăng ký kết hôn ở đâu, mất bao lâu?',
  'Lệ phí làm hộ chiếu là bao nhiêu?',
  'Thủ tục đăng ký hộ kinh doanh?',
]

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const listRef = useRef<FlatList>(null)

  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 100)
    }
  }, [messages, loading])

  async function send(text: string) {
    const question = text.trim()
    if (!question || loading) return
    setInput('')
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: question }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)
    try {
      const res = await fetch(AGENT_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: question }),
      })
      const data = await res.json()
      const reply = data.response ?? data.error ?? 'Đã xảy ra lỗi.'
      setMessages(prev => [...prev, { id: (Date.now() + 1).toString(), role: 'assistant', content: reply }])
    } catch {
      setMessages(prev => [...prev, { id: (Date.now() + 1).toString(), role: 'assistant', content: 'Không thể kết nối. Vui lòng thử lại.' }])
    } finally {
      setLoading(false)
    }
  }

  const renderItem: ListRenderItem<Message> = ({ item }) => (
    <View style={[styles.row, item.role === 'user' ? styles.rowUser : styles.rowBot]}>
      {item.role === 'assistant' && <Text style={styles.avatar}>🏛️</Text>}
      <View style={[styles.bubble, item.role === 'user' ? styles.bubbleUser : styles.bubbleBot]}>
        {item.role === 'assistant' ? (
          <Markdown style={markdownStyles}>{item.content}</Markdown>
        ) : (
          <Text style={styles.userText}>{item.content}</Text>
        )}
      </View>
    </View>
  )

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={90}
    >
      {messages.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyTitle}>Xin chào! 👋</Text>
          <Text style={styles.emptySubtitle}>Hỏi tôi về thủ tục hành chính:</Text>
          {SUGGESTED.map(q => (
            <TouchableOpacity key={q} style={styles.suggestion} onPress={() => send(q)}>
              <Text style={styles.suggestionText}>{q}</Text>
            </TouchableOpacity>
          ))}
        </View>
      ) : (
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={m => m.id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          ListFooterComponent={loading ? (
            <View style={[styles.row, styles.rowBot]}>
              <Text style={styles.avatar}>🏛️</Text>
              <View style={styles.bubbleBot}>
                <ActivityIndicator size="small" color="#1d4ed8" />
              </View>
            </View>
          ) : null}
        />
      )}

      <View style={styles.inputBar}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="Nhập câu hỏi..."
          placeholderTextColor="#9ca3af"
          multiline
          maxLength={500}
          editable={!loading}
        />
        <TouchableOpacity
          style={[styles.sendBtn, (!input.trim() || loading) && styles.sendBtnDisabled]}
          onPress={() => send(input)}
          disabled={!input.trim() || loading}
        >
          <Text style={styles.sendText}>Gửi</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  list: { padding: 12, gap: 10 },
  row: { flexDirection: 'row', marginVertical: 4, alignItems: 'flex-start' },
  rowUser: { justifyContent: 'flex-end' },
  rowBot: { justifyContent: 'flex-start' },
  avatar: { fontSize: 20, marginRight: 6, marginTop: 4 },
  bubble: { maxWidth: '80%', borderRadius: 16, padding: 12 },
  bubbleUser: { backgroundColor: '#1d4ed8', borderTopRightRadius: 4 },
  bubbleBot: { backgroundColor: '#ffffff', borderTopLeftRadius: 4, borderWidth: 1, borderColor: '#e5e7eb', shadowColor: '#000', shadowOpacity: 0.05, shadowOffset: { width: 0, height: 1 } },
  userText: { color: '#fff', fontSize: 14, lineHeight: 20 },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  emptyTitle: { fontSize: 20, fontWeight: 'bold', color: '#1d4ed8', marginBottom: 6 },
  emptySubtitle: { color: '#6b7280', marginBottom: 16, fontSize: 14 },
  suggestion: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#bfdbfe', borderRadius: 12, paddingHorizontal: 16, paddingVertical: 10, marginBottom: 8, width: '100%' },
  suggestionText: { color: '#1d4ed8', fontSize: 14 },
  inputBar: { flexDirection: 'row', padding: 10, backgroundColor: '#fff', borderTopWidth: 1, borderTopColor: '#e5e7eb', gap: 8 },
  input: { flex: 1, borderWidth: 1, borderColor: '#d1d5db', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 10, fontSize: 14, color: '#111827', maxHeight: 100 },
  sendBtn: { backgroundColor: '#1d4ed8', borderRadius: 12, paddingHorizontal: 18, justifyContent: 'center' },
  sendBtnDisabled: { opacity: 0.4 },
  sendText: { color: '#fff', fontWeight: '600', fontSize: 14 },
})

const markdownStyles = StyleSheet.create({
  body: { fontSize: 14, lineHeight: 20, color: '#111827' },
  strong: { fontWeight: '700' },
  bullet_list: { marginVertical: 2 },
  ordered_list: { marginVertical: 2 },
  list_item: { marginVertical: 1 },
  h2: { fontSize: 14, fontWeight: '700', marginVertical: 4 },
})
