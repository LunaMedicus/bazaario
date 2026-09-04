import React from "react";
import { playClick } from "../sound";

function StarRating({ value, onChange }) {
  return (
    <div className="star-rating" role="radiogroup" aria-label="Rating">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          className={star <= value ? "star active" : "star"}
          onClick={() => {
            playClick();
            onChange(star);
          }}
          aria-label={`${star} star${star > 1 ? "s" : ""}`}
          role="radio"
          aria-checked={star === value}
        >
          ★
        </button>
      ))}
    </div>
  );
}

export default StarRating;
