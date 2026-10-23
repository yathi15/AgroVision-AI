import { useState } from "react";

export default function ImageUpload({ onSelect, label = "Upload a photo" }) {
  const [preview, setPreview] = useState(null);

  const handleFile = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setPreview(URL.createObjectURL(file));
    onSelect(file);
  };

  return (
    <div className="image-upload">
      <label>{label}</label>
      <input type="file" accept="image/*" capture="environment" onChange={handleFile} />
      {preview && <img src={preview} alt="preview" style={{ maxWidth: 300, borderRadius: 8 }} />}
    </div>
  );
}