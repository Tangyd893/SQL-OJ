interface StepperControlProps {
  value: number
  min: number
  max: number
  step: number
  format: (value: number) => string
  onChange: (value: number) => void
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

export function StepperControl({
  value,
  min,
  max,
  step,
  format,
  onChange,
}: StepperControlProps) {
  const bump = (delta: number) => {
    const next = clamp(Math.round((value + delta) / step) * step, min, max)
    onChange(Number(next.toFixed(4)))
  }

  return (
    <div className="stepper-control">
      <div className="stepper-buttons">
        <button
          type="button"
          className="stepper-btn"
          aria-label="减小"
          disabled={value <= min}
          onClick={() => bump(-step)}
        >
          −
        </button>
        <span className="stepper-value">{format(value)}</span>
        <button
          type="button"
          className="stepper-btn"
          aria-label="增大"
          disabled={value >= max}
          onClick={() => bump(step)}
        >
          +
        </button>
      </div>
      <input
        type="range"
        className="stepper-range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  )
}
