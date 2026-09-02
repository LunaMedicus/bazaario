import React from "react";
import clickSound from "../sounds/star-click.mp3";

function StarRating({ value, onChange }) {
  return (
    <div className="star-rating" role="radiogroup" aria-label="Rating">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          className={star <= value ? "star active" : "star"}
          onClick={() => {
          const audio = new Audio(clickSound);
          audio.currentTime = 0;
          audio.play();
          onChange(star);
          }}
          aria-label={`${star} star${star > 1 ? "s" : ""}`}
          aria-pressed={star === value}
        >
          ★
        </button>
      ))}
    </div>
  );
}

export default StarRating;
