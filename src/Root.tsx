import { HelloWorldCompositions } from "./compositions/cases/hello-world/register";
import { GitHubTrendingCompositions } from "./compositions/cases/github-trending/register";
import { NovelCompositions } from "./compositions/cases/novel/register";
import { PythagoreanTheoremCompositions } from "./compositions/cases/pythagorean-theorem/register";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <HelloWorldCompositions />
      <GitHubTrendingCompositions />
      <NovelCompositions />
      <PythagoreanTheoremCompositions />
    </>
  );
};