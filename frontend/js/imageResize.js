/**
 * Redimensiona una imagen a max 1200px en el cliente antes de subir.
 * Usa canvas (no depende de librerías).
 */
(function () {
  const imageResize = {
    MAX_WIDTH: 1200,
    QUALITY: 0.85,

    /**
     * Devuelve una Promise<File> con la imagen redimensionada como JPEG.
     * Si la imagen ya es más chica, la devuelve igual pero en JPEG.
     */
    resize(file) {
      return new Promise((resolve, reject) => {
        if (!file.type.startsWith("image/")) {
          reject(new Error("El archivo no es una imagen"));
          return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
          const img = new Image();
          img.onload = () => {
            try {
              const canvas = document.createElement("canvas");
              let { width, height } = img;

              if (width > this.MAX_WIDTH) {
                const ratio = this.MAX_WIDTH / width;
                width = this.MAX_WIDTH;
                height = Math.round(img.height * ratio);
              }

              canvas.width = width;
              canvas.height = height;
              const ctx = canvas.getContext("2d");
              ctx.drawImage(img, 0, 0, width, height);

              canvas.toBlob(
                (blob) => {
                  if (!blob) {
                    reject(new Error("Error al comprimir la imagen"));
                    return;
                  }
                  const newFile = new File(
                    [blob],
                    file.name.replace(/\.[^.]+$/, "") + ".jpg",
                    { type: "image/jpeg" }
                  );
                  resolve(newFile);
                },
                "image/jpeg",
                this.QUALITY
              );
            } catch (err) {
              reject(err);
            }
          };
          img.onerror = () => reject(new Error("No se pudo cargar la imagen"));
          img.src = e.target.result;
        };
        reader.onerror = () => reject(new Error("No se pudo leer el archivo"));
        reader.readAsDataURL(file);
      });
    },
  };

  window.imageResize = imageResize.resize.bind(imageResize);
})();
