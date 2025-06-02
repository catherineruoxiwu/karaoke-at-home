"use client"

import { useEffect, useRef, useState } from "react"

export default function YouTubePage() {
  const [videoId, setVideoId] = useState<string | null>(null)
  const [audioPath, setAudioPath] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const playerRef = useRef<any>(null)

  // 1. Load YouTube IFrame API safely
  useEffect(() => {
    const scriptTag = document.createElement("script")
    scriptTag.src = "https://www.youtube.com/iframe_api"
    scriptTag.async = true
    document.body?.appendChild(scriptTag)

    // 2. Attach player loader once API is ready
    ;(window as any).onYouTubeIframeAPIReady = () => {
      loadNextSong()
    }
  }, [])

  // 3. Load next song from backend
  const loadNextSong = async () => {
    try {
      const res = await fetch("http://localhost:8000/songs/play", { method: "POST" })
      if (!res.ok) throw new Error("No songs available")

      const song = await res.json()
      const ytId = extractYouTubeId(song.youtube_url)
      setVideoId(ytId)
      setAudioPath(song.instrumental)

      // 4. Create player if not created
      if (!playerRef.current) {
        playerRef.current = new (window as any).YT.Player("ytplayer", {
          videoId: ytId,
          playerVars: { autoplay: 1, mute: 1, controls: 0 },
          events: {
            onReady: () => {
              audioRef.current?.play()
            },
            onStateChange: (event: any) => {
              // On end
              if (event.data === 0) {
                loadNextSong()
              }
            }
          }
        })
      } else {
        playerRef.current.loadVideoById(ytId)
        audioRef.current?.play()
      }
    } catch (err) {
      console.warn("No songs to play or error:", err)
      setVideoId(null)
    }
  }

  // 5. Utility to extract video ID
  const extractYouTubeId = (url: string) => {
    const match = url.match(/(?:v=|\/)([0-9A-Za-z_-]{11})/)
    return match ? match[1] : ""
  }

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      {videoId ? (
        <div className="w-full max-w-6xl aspect-video relative">
          <div id="ytplayer" className="w-full h-full rounded-lg" />
          {audioPath && (
            <audio ref={audioRef} src={`http://localhost:8000/${audioPath}`} autoPlay hidden />
          )}
        </div>
      ) : (
        <div className="text-white text-xl">No songs in queue</div>
      )}
    </div>
  )
}
