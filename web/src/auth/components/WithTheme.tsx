import React from 'react';
import { ThemeProvider, useTheme } from '@aws-amplify/ui-react';
import { Theme } from '@aws-amplify/ui-react';
import createCustomTheme from '@/src/utils/amplify-theme-utils';

// HOC to wrap a component with ThemeProvider and apply a custom theme
const withTheme = <P extends object>(Component: React.ComponentType<P>) => {
  return (props: P) => {
    const { tokens } = useTheme();

    const theme: Theme = createCustomTheme(tokens);

    return (
      <ThemeProvider theme={theme}>
        <Component {...props} />
      </ThemeProvider>
    );
  };
};

export default withTheme;
