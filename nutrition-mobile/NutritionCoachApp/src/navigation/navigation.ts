export interface Recipe {
    id: number;
    recipe_name: string;
    ingredients: string;
    instructions: string;
    macros: string;
}

export type RootStackParamList = {
    Auth: undefined;
    Main: undefined;
};

export type MainTabParamList = {
    Home: undefined;
    Recipes: undefined;
    Grocery: undefined;
    Preferences: undefined;
};

export type RecipeStackParamList = {
    GenerateRecipe: undefined;
    Instruction: { recipe: Recipe };
};

declare global {
    namespace ReactNavigation {
        interface RootParamList extends RootStackParamList {}
    }
}