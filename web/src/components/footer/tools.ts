export function selectFile() {
  const selector = document.getElementById('file_selector')
  if (selector) {
    selector.click()
  }
}

export function getUploadFile(): File | undefined {
  // http://www.feingto.com/?p=14158
  const eFile = document.getElementById('file_selector') as HTMLInputElement
  if (eFile.files == null) {
    return undefined
  }

  if (eFile.files.length !== 1) {
    return undefined
  }

  return eFile.files[0]


}
