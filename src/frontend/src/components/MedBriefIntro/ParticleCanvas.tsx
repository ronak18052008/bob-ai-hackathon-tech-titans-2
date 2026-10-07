import { useEffect, useRef } from 'react'

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  alpha: number
  baseAlpha: number
  colorIdx: number
}

interface ParticleCanvasProps {
  intensity?: number // 0 to 1
}

export function ParticleCanvas({ intensity = 1 }: ParticleCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationFrameId: number
    let width = (canvas.width = window.innerWidth)
    let height = (canvas.height = window.innerHeight)

    const handleResize = () => {
      if (!canvas) return
      width = canvas.width = window.innerWidth
      height = canvas.height = window.innerHeight
    }

    window.addEventListener('resize', handleResize)

    // Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    // Generate subtle particles
    const particleCount = Math.min(Math.floor((width * height) / 32000), 45)
    const particles: Particle[] = []

    for (let i = 0; i < particleCount; i++) {
      const baseAlpha = Math.random() * 0.35 + 0.2
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35 - 0.1, // subtle upward drift
        radius: Math.random() * 1.5 + 1.0,
        alpha: baseAlpha,
        baseAlpha,
        colorIdx: i % 3,
      })
    }

    const palette = [
      '2, 132, 199', // Medical Blue (#0284c7)
      '10, 92, 54',  // MedBrief Emerald Teal (#0a5c36)
      '217, 119, 6', // MedBrief Gold Amber (#d97706)
    ]

    const render = () => {
      ctx.clearRect(0, 0, width, height)

      // Draw subtle network lines between nearby particles
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x
          const dy = particles[i].y - particles[j].y
          const dist = Math.sqrt(dx * dx + dy * dy)

          if (dist < 90) {
            const lineAlpha = (1 - dist / 90) * 0.15 * intensity
            ctx.beginPath()
            ctx.strokeStyle = `rgba(2, 132, 199, ${lineAlpha})`
            ctx.lineWidth = 0.75
            ctx.moveTo(particles[i].x, particles[i].y)
            ctx.lineTo(particles[j].x, particles[j].y)
            ctx.stroke()
          }
        }
      }

      // Draw and update particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i]
        const rgb = palette[p.colorIdx]

        ctx.beginPath()
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${rgb}, ${p.alpha * intensity})`
        ctx.shadowBlur = 4
        ctx.shadowColor = `rgba(${rgb}, 0.3)`
        ctx.fill()
        ctx.shadowBlur = 0

        if (!prefersReducedMotion) {
          p.x += p.vx
          p.y += p.vy

          // Wrap edges
          if (p.x < 0) p.x = width
          if (p.x > width) p.x = 0
          if (p.y < 0) p.y = height
          if (p.y > height) p.y = 0
        }
      }

      if (!prefersReducedMotion) {
        animationFrameId = requestAnimationFrame(render)
      }
    }

    render()

    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animationFrameId)
    }
  }, [intensity])

  return <canvas ref={canvasRef} className="particle-canvas" aria-hidden="true" />
}
