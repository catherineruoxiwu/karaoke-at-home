// Updated KTVHome with backend API integration
"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Music, ChevronUp, ChevronDown, Trash2, Loader2, Shuffle, Check, Globe } from "lucide-react"

interface Song {
  id: number
  title: string
  artist: string
  addedBy?: string
  status: "ready" | "processing"
}

type Language = "en" | "zh" | "ja" | "ko"

const translations = {
  en: {
    title: "KTV @ Home",
    songRequester: "Song requester",
    urlLink: "URL link",
    addSong: "Add Song",
    songQueue: "Song Queue",
    songsInQueue: "songs in the queue",
    shuffle: "Shuffle",
    noSongs: "No songs in the queue yet",
    addFirstSong: "Add your first song using the form above!",
    addedBy: "Added by",
  },
  zh: {
    title: "KTV @ Home",
    songRequester: "点歌人",
    urlLink: "URL 链接",
    addSong: "添加歌曲",
    songQueue: "歌曲队列",
    songsInQueue: "首歌曲在队列中",
    shuffle: "随机播放",
    noSongs: "队列中还没有歌曲",
    addFirstSong: "使用上面的表单添加您的第一首歌曲！",
    addedBy: "添加者",
  },
  ja: {
    title: "KTV @ Home",
    songRequester: "リクエスト者",
    urlLink: "URL リンク",
    addSong: "曲を追加",
    songQueue: "曲のキュー",
    songsInQueue: "曲がキューにあります",
    shuffle: "シャッフル",
    noSongs: "キューにはまだ曲がありません",
    addFirstSong: "上のフォームを使って最初の曲を追加してください！",
    addedBy: "追加者",
  },
  ko: {
    title: "KTV @ Home",
    songRequester: "신청자",
    urlLink: "URL 링크",
    addSong: "노래 추가",
    songQueue: "노래 대기열",
    songsInQueue: "곡이 대기열에 있습니다",
    shuffle: "셔플",
    noSongs: "대기열에 아직 노래가 없습니다",
    addFirstSong: "위의 양식을 사용하여 첫 번째 노래를 추가하세요!",
    addedBy: "추가자",
  },
}

const BACKEND_BASE = "http://localhost:8000" // TODO

export default function KTVHome() {
  const [language, setLanguage] = useState<Language>("zh")
  const [songTitle, setSongTitle] = useState("")
  const [youtubeUrl, setYoutubeUrl] = useState("")
  const [songs, setSongs] = useState<Song[]>([])

  const t = translations[language]

  useEffect(() => {
    fetchSongs()
  }, [])

  const fetchSongs = async () => {
    const res = await fetch(`${BACKEND_BASE}/songs`)
    const data = await res.json()
    setSongs(
      data.map((s: any) => ({
        id: s.id,
        title: s.title,
        artist: s.singer,
        status: s.status === "done" ? "ready" : "processing",
      }))
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!songTitle.trim() || !youtubeUrl.trim()) return
    await fetch(`${BACKEND_BASE}/songs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: songTitle.trim(),
        url: youtubeUrl.trim(),
      }),
    })
    setSongTitle("")
    setYoutubeUrl("")
    fetchSongs()
  }

  const deleteSong = async (id: number) => {
    await fetch(`${BACKEND_BASE}/songs/${id}`, {
      method: "DELETE",
    })
    fetchSongs()
  }

  const moveSong = async (id: number, direction: "up" | "down") => {
    await fetch(`${BACKEND_BASE}/songs/${id}/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction }),
    })
    fetchSongs()
  }

  const shuffleSongs = async () => {
    await fetch(`${BACKEND_BASE}/songs/shuffle`, {
      method: "POST",
    })
    fetchSongs()
  }

  const cycleLanguage = () => {
    const languages: Language[] = ["zh", "en", "ja", "ko"]
    const currentIndex = languages.indexOf(language)
    const nextIndex = (currentIndex + 1) % languages.length
    setLanguage(languages[nextIndex])
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900">
      <div className="sticky top-0 z-50 bg-black backdrop-blur-md border-b border-white/10">
        <div className="container mx-auto px-4 py-6">
          <div className="flex flex-col space-y-4">
            <div className="flex items-center justify-between">
              <h1 className="text-3xl md:text-4xl font-bold text-white flex items-center gap-3">
                <Music className="h-8 w-8 text-purple-400" />
                {t.title}
              </h1>
              <Button
                onClick={cycleLanguage}
                variant="ghost"
                size="sm"
                className="text-white hover:bg-white/10 hover:text-white"
              >
                <Globe className="h-4 w-4 mr-1" />
                {language.toUpperCase()}
              </Button>
            </div>
            <form onSubmit={handleSubmit} className="flex flex-col md:flex-row gap-3">
              <Input
                type="text"
                placeholder={t.songRequester}
                value={songTitle}
                onChange={(e) => setSongTitle(e.target.value)}
                className="flex-1 bg-white/10 border-white/20 text-white placeholder:text-white/60"
              />
              <Input
                type="text"
                placeholder={t.urlLink}
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                className="flex-1 bg-white/10 border-white/20 text-white placeholder:text-white/60"
              />
              <Button type="submit" className="bg-purple-600 hover:bg-purple-700 text-white px-8">
                {t.addSong}
              </Button>
            </form>
          </div>
        </div>
      </div>
      <div className="container mx-auto px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-white mb-2">{t.songQueue}</h2>
            <p className="text-white/70">
              {songs.length} {t.songsInQueue}
            </p>
          </div>
          <Button onClick={shuffleSongs} variant="ghost" className="text-white hover:bg-white/10 hover:text-white">
            <Shuffle className="h-4 w-4 mr-2" />
            {t.shuffle}
          </Button>
        </div>
        <div className="grid gap-3">
          {songs.map((song, index) => (
            <Card key={song.id} className="bg-indigo-50 border-indigo-200 hover:bg-indigo-100 transition-all duration-200">
              <CardContent className="p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3 flex-1">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-indigo-900 text-base">{song.title}</h3>
                        {song.status === "processing" ? (
                          <Loader2 className="h-4 w-4 min-w-4 text-yellow-600 animate-spin" />
                        ) : (
                          <Check className="h-4 w-4 min-w-4 text-green-600" />
                        )}
                      </div>
                      <p className="text-indigo-700 text-sm">
                        {t.songRequester}: {song.artist}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => moveSong(song.id, "up")}
                      className="h-6 w-6 p-0 text-indigo-600 hover:bg-indigo-100"
                    >
                      <ChevronUp className="h-3 w-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => moveSong(song.id, "down")}
                      className="h-6 w-6 p-0 text-indigo-600 hover:bg-indigo-100"
                    >
                      <ChevronDown className="h-3 w-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => deleteSong(song.id)}
                      className="h-6 w-6 p-0 text-red-600 hover:bg-red-50"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        {songs.length === 0 && (
          <div className="text-center py-12">
            <Music className="h-16 w-16 text-white/30 mx-auto mb-4" />
            <p className="text-white/60 text-lg">{t.noSongs}</p>
            <p className="text-white/40">{t.addFirstSong}</p>
          </div>
        )}
      </div>
    </div>
  )
}