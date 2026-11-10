import Landing from './landing/Landing';

export default function App() {
  return (
    <Landing
      onUpload={(file) => {
        // TODO (Person B): sign in with Google, then POST the file to /imports.
        console.info('Ready to upload', file.name);
      }}
    />
  );
}
