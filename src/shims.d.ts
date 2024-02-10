// Avoids typescript error when importing files
declare module '*.vue'
declare module 'import.meta' {
    const url: string
    export default url
}